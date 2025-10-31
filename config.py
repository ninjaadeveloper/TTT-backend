import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    APP_ENV = "local"
    PORT = int(os.getenv("PORT", 8000))
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET = os.getenv("JWT_SECRET")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./storage/uploads")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # groq or gemini
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    SPEECH_PROVIDER = os.getenv("SPEECH_PROVIDER", "whisper")
    SPEECH_API_KEY = os.getenv("SPEECH_API_KEY")  # <-- yahan # use karo
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

