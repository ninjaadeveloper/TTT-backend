from celery_worker import celery
from core.ai_pipeline import process_upload
import os
import traceback


@celery.task(name="tasks.process_upload_task")
def process_upload_task(upload_id, file_path, user_id, language=None):
    try:
        print(f"🚀 [Celery Task] Starting process for upload_id={upload_id}")
        print(f"📁 File path received: {file_path}")
        print(f"👤 User ID: {user_id}, 🌐 Language: {language}")

        # Confirm file exists before processing
        if not os.path.exists(file_path):
            print(f"⚠️ File not found at path: {file_path}")
            print(f"🔍 Current working directory: {os.getcwd()}")
            print(f"📂 Directory listing: {os.listdir(os.path.dirname(file_path) or '.')}")
        
        # Run the AI pipeline
        result = process_upload(upload_id, file_path, user_id, language=language)
        print(f"✅ [Celery Task] Upload {upload_id} processed successfully.")

        # Clean up local file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 [Cleanup] Deleted local file: {file_path}")
        except Exception as cleanup_err:
            print(f"⚠️ [Cleanup Error] {cleanup_err}")

        return result

    except Exception as e:
        print("❌ [Celery Task Error]:", e)
        traceback.print_exc()
        return {"error": str(e)}
