from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from api.auth import bp as auth_bp
from api.upload import bp as up_bp
from api.notes import bp as notes_bp
from api.health import bp as health_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS (allow all origins for local testing)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(up_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(health_bp)

    # ✅ Default route for testing
    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"message": "TalkToText Backend Server Running ✅"}), 200

    return app


if __name__ == "__main__":
    app = create_app()

    # 🧠 Smart switch based on environment
    if getattr(Config, "APP_ENV", "local") == "local":
        app.run(host="127.0.0.1", port=getattr(Config, "PORT", 8000), debug=True)
    else:
        app.run(host="0.0.0.0", port=getattr(Config, "PORT", 8000))
