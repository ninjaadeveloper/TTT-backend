import os
import subprocess
import sys

def download_meeting_audio(meeting_url):
    print(f"🎧 [Download] Fetching audio from: {meeting_url}")
    try:
        # ✅ Always resolve absolute path to backend root
        backend_root = os.path.dirname(os.path.abspath(__file__))
        while not backend_root.endswith("talktotext-backend"):
            backend_root = os.path.dirname(backend_root)

        uploads_dir = os.path.join(backend_root, "storage", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        # ✅ Output path inside uploads
        output_path = os.path.join(uploads_dir, "meeting_audio.%(ext)s")

        # ✅ yt-dlp via Python executable (works inside venv)
        command = [
            sys.executable, "-m", "yt_dlp",
            "--extract-audio", "--audio-format", "mp3",
            "-o", output_path,
            meeting_url
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ [Download Meeting Audio] yt-dlp failed:\n{result.stderr}")
            raise Exception(result.stderr)

        # Replace %(ext)s with actual extension
        final_path = output_path.replace("%(ext)s", "mp3")

        # If yt-dlp used video title instead, auto-locate the .mp3
        if not os.path.exists(final_path):
            for f in os.listdir(uploads_dir):
                if f.endswith(".mp3"):
                    final_path = os.path.join(uploads_dir, f)
                    break

        print(f"✅ [Download] Audio saved to: {final_path}")
        return final_path

    except Exception as e:
        print(f"❌ [Download Meeting Audio] Error: {e}")
        raise
