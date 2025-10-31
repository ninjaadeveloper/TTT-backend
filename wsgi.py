from app import create_app
from config import Config

# Flask application instance
app = create_app()

# ─── Entry point ────────────────────────────────
if __name__ == "__main__":
    if Config.APP_ENV == "local":
        # Local development mode
        app.run(host="127.0.0.1", port=Config.PORT, debug=True)
    else:
        # Production mode (Railway / Gunicorn)
        app.run(host="0.0.0.0", port=Config.PORT)
