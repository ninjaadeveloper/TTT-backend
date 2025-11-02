from flask import Blueprint, request, jsonify
from models.mongo_models import users
from jose import jwt
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# --- Helper to create JWT token ---
def create_token(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")

# --- Register ---
@bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    print("📩 Incoming registration data:", data)
    required = ["name", "email", "phone", "password"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "Email already exists"}), 400

    user = {
        "name": data["name"],
        "email": data["email"].lower().strip(),
        "phone": data["phone"],
        "password": generate_password_hash(data["password"]),
        "created_at": datetime.utcnow()
    }

    res = users.insert_one(user)
    token = create_token(res.inserted_id)

    return jsonify({
        "message": "User registered successfully",
        "token": token,
        "user": {
            "id": str(res.inserted_id),
            "name": user["name"],
            "email": user["email"],
            "phone": user["phone"]
        }
    }), 201

# --- Login ---
@bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}

    if "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    user = users.find_one({"email": data["email"].lower().strip()})
    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user["_id"])

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user["email"],
            "phone": user.get("phone")
        }
    }), 200
