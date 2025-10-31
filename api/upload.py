from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os, uuid, requests, subprocess, re
from datetime import datetime
from models.mongo_models import uploads
from core.ai_pipeline import process_upload
from core.tasks import process_upload_task
from jose import jwt
from config import Config

bp = Blueprint("upload", __name__, url_prefix="/api")

ALLOWED = {"wav", "mp3", "mp4", "m4a", "webm"}
TEMP_DIR = "tmp_downloads"
os.makedirs(TEMP_DIR, exist_ok=True)


# ------------------------------- helpers -------------------------------

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def get_user_from_auth():
    auth = request.headers.get("Authorization", "")
    if not auth:
        return "demo_user"
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            return str(payload.get("sub", "demo_user"))
        except Exception:
            return "demo_user"
    return "demo_user"


def upload_file_to_assemblyai(file_obj):
    headers = {"authorization": Config.SPEECH_API_KEY}
    response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=file_obj)
    response.raise_for_status()
    return response.json()["upload_url"]


# ------------------------------- URL DOWNLOAD HANDLER -------------------------------

def download_audio_from_url(url: str):
    """Download YouTube or Google Drive audio and return local file path"""
    unique_name = f"{uuid.uuid4().hex}.mp3"
    local_path = os.path.join(TEMP_DIR, unique_name)

    # --- YouTube URL ---
    if "youtube.com" in url or "youtu.be" in url:
        print(f"🎧 [Download] Fetching audio from YouTube: {url}")
        try:
            subprocess.run(
                [
                    os.path.join(os.getcwd(), "venv", "Scripts", "python.exe"),
                    "-m", "yt_dlp",
                    "-x", "--audio-format", "mp3",
                    "-o", local_path,
                    url
                ],
                check=True,
                capture_output=True,
                text=True
            )
            return local_path
        except subprocess.CalledProcessError as e:
            print("❌ [YouTube Download Error]:", e.stderr)
            raise Exception(f"yt-dlp failed: {e.stderr}")

    # --- Google Drive URL ---
    elif "drive.google.com" in url:
        print(f"🧩 [Download] Fetching audio from Google Drive: {url}")
        try:
            file_id_match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
            if not file_id_match:
                raise Exception("Invalid Google Drive URL format")
            file_id = file_id_match.group(1)
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return local_path
        except Exception as e:
            raise Exception(f"Google Drive download failed: {e}")

    else:
        raise Exception("Unsupported URL source. Only YouTube or Google Drive allowed.")


# ------------------------------- main route -------------------------------

@bp.route("/upload", methods=["POST"])
def upload_file():
    user_id = get_user_from_auth()
    f = request.files.get("file")
    url = request.form.get("url") or (request.json.get("url") if request.is_json else None)
    print("📥 Received:", f, url)
    language = request.form.get("language") or request.args.get("language") or "auto"
    background = request.form.get("background", "true").lower() != "false"

    try:
        extract_duration = int(
            request.form.get("extractDuration")
            or (request.json.get("extractDuration") if request.is_json else 0)
        )
    except Exception:
        extract_duration = 0

    if not f and not url:
        return jsonify({"error": "file or url required"}), 400

    uid = str(uuid.uuid4())

    # ---------------- handle direct file upload ----------------
    if f:
        # check by filename OR mimetype
        ext = None
        if "." in f.filename:
            ext = f.filename.rsplit(".", 1)[1].lower()
        else:
            # fallback to mimetype
            mime = f.mimetype.lower()
            if "webm" in mime:
                ext = "webm"
            elif "mp3" in mime:
                ext = "mp3"
            elif "mp4" in mime:
                ext = "mp4"
            elif "wav" in mime:
                ext = "wav"
            elif "m4a" in mime:
                ext = "m4a"

        if ext not in ALLOWED:
            print(f"❌ Unsupported file type: {f.filename} ({f.mimetype})")
            return jsonify({"error": "unsupported file type"}), 400

        filename = secure_filename(f.filename or f"recording.{ext}")

        # upload to AssemblyAI
        upload_url = upload_file_to_assemblyai(f)

    # ---------------- handle meeting / video URL ----------------
    else:
        try:
            print("🌐 [URL Detected] Downloading meeting/video audio...")
            local_audio_path = download_audio_from_url(url)
            print(f"✅ [Downloaded] Audio saved locally: {local_audio_path}")

            with open(local_audio_path, "rb") as audio_file:
                upload_url = upload_file_to_assemblyai(audio_file)

            filename = os.path.basename(local_audio_path)

            # delete local temp file after upload
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)

        except Exception as e:
            print(f"❌ [Meeting URL Error]: {e}")
            return jsonify({"error": f"Failed to process meeting URL: {str(e)}"}), 500

    # ---------------- insert upload info into Mongo ----------------
    uploads.insert_one({
        "_id": uid,
        "user_id": user_id,
        "filename": filename,
        "upload_url": upload_url,
        "status": "uploaded",
        "created_at": datetime.utcnow(),
        "progress": {"stage": "uploaded", "percent": 0},
        "language": language,
        "extract_duration": extract_duration
    })

    # ---------------- trigger processing (sync or background) ----------------
    if background:
        process_upload_task.delay(uid, upload_url, user_id, language)
        return jsonify({"upload_id": uid}), 201
    else:
        note_id = process_upload(uid, upload_url, user_id, language=language)
        return jsonify({
            "upload_id": uid,
            "note_id": str(note_id),
            "extract_duration": extract_duration
        }), 201


# ------------------------------- check status -------------------------------

@bp.route("/status/<upload_id>", methods=["GET"])
def status(upload_id):
    u = uploads.find_one({"_id": upload_id}, {"status": 1, "note_id": 1, "progress": 1, "extract_duration": 1})
    if not u:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "status": u.get("status"),
        "note_id": str(u.get("note_id")),
        "progress": u.get("progress", {}),
        "extract_duration": u.get("extract_duration", 0)
    })
