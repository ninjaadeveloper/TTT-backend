from flask import Blueprint, jsonify, send_file, request
from models.mongo_models import notes
from core.utils import export_to_pdf, export_to_docx
from bson import ObjectId
from jose import jwt, JWTError
from config import Config
import os
import traceback

bp = Blueprint('notes', __name__, url_prefix='/api')


# ------------------ AUTH HELPER ------------------
def get_user_from_auth():
    """
    Extract user_id from JWT.
    Falls back to 'demo_user' if token is invalid or missing.
    """
    auth = request.headers.get("Authorization", "")
    if not auth:
        return "demo_user"

    try:
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return "demo_user"

        token = parts[1]
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        user_id = str(payload.get("sub"))  # sub → user_id stored in JWT
        print(user_id)
        return user_id if user_id else "demo_user"
    except JWTError:
        # Invalid / expired token
        return "demo_user"
    except Exception as e:
        print("⚠️ [get_user_from_auth] Error decoding token:", e)
        traceback.print_exc()
        return "demo_user"


# ------------------ DB HELPERS ------------------
def get_note_by_id(note_id: str):
    """Fetch note by either string _id or ObjectId."""
    try:
        n = notes.find_one({"_id": ObjectId(note_id)})
        if not n:
            n = notes.find_one({"_id": note_id})
        return n
    except Exception:
        return None


# ------------------ ROUTES ------------------
@bp.route('/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """Return single note details by ID"""
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found"}), 404

    return jsonify({
        "note_id": str(n["_id"]),
        "final_notes": n.get("final_notes", ""),
        "raw_transcript": n.get("raw_transcript", ""),
        "cleaned_transcript": n.get("cleaned_transcript", ""),
        "created_at": n["created_at"].isoformat() if n.get("created_at") else None
    })


@bp.route('/history', methods=['GET'])
def history():
    """Return logged-in user's history of processed notes"""
    user_id = get_user_from_auth()
    print("🧠 HISTORY DEBUG — user_id from JWT:", user_id)
    # 🔒 Block guests
    if user_id == "demo_user":
        return jsonify({"error": "Login required to view history"}), 401

    # 🔍 Fetch user-specific notes
    try:
        docs = list(notes.find({"user_id": user_id}).sort("created_at", -1).limit(50))
        if not docs:
            # In case some old notes stored user_id as ObjectId
            docs = list(notes.find({"user_id": ObjectId(user_id)}).sort("created_at", -1).limit(50))
    except Exception as e:
        print("⚠️ [history] DB fetch error:", e)
        docs = []

    history_data = [
        {
            "note_id": str(d["_id"]),
            "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
            "summary_preview": (d.get("final_notes", "")[:120] + "...") if d.get("final_notes") else ""
        }
        for d in docs
    ]

    return jsonify(history_data)


@bp.route('/download/pdf/<note_id>', methods=['GET'])
def download_pdf(note_id):
    """Download note as PDF"""
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found in DB"}), 404

    os.makedirs("storage/exports", exist_ok=True)
    path = f"storage/exports/{note_id}.pdf"
    export_to_pdf(n.get("final_notes", ""), path)
    return send_file(path, as_attachment=True, mimetype="application/pdf")


@bp.route('/download/docx/<note_id>', methods=['GET'])
def download_docx(note_id):
    """Download note as DOCX"""
    n = get_note_by_id(note_id)
    if not n:
        return jsonify({"error": "Note not found in DB"}), 404

    os.makedirs("storage/exports", exist_ok=True)
    path = f"storage/exports/{note_id}.docx"
    export_to_docx(n.get("final_notes", ""), path)
    return send_file(path, as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
