from celery_worker import celery
from core.ai_pipeline import process_upload
import os
import traceback


@celery.task(name="tasks.process_upload_task")
def process_upload_task(upload_id, file_path, user_id, language=None):
    """
    Background Celery task for processing uploads.
    Cleans up temporary local files (like meeting_audio.mp3)
    after successful transcription.
    """

    try:
        print(f"🚀 [Celery Task] Starting process for upload_id={upload_id}")

        # 1️⃣ Run the AI processing pipeline (AssemblyAI, translation, summarization)
        result = process_upload(upload_id, file_path, user_id, language=language)
        print(f"✅ [Celery Task] Upload {upload_id} processed successfully.")

        # 2️⃣ Try cleaning up local file if it exists (to save disk space)
        try:
            # Check direct path
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 [Cleanup] Deleted local file: {file_path}")
            else:
                # Check relative path (e.g., "storage/uploads/...mp3")
                abs_path = os.path.join(os.getcwd(), file_path)
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                    print(f"🧹 [Cleanup] Deleted local file: {abs_path}")
        except Exception as cleanup_err:
            print(f"⚠️ [Cleanup Error] Could not delete file: {cleanup_err}")

        # 3️⃣ Convert Mongo ObjectIds to string for JSON-safe return
        if isinstance(result, dict):
            if "_id" in result:
                result["_id"] = str(result["_id"])
            if "note_id" in result:
                result["note_id"] = str(result["note_id"])

        return result

    except Exception as e:
        print("❌ [Celery Task Error]", e)
        traceback.print_exc()
        return {"error": str(e)}
