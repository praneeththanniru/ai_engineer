from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from .models import User
from .extensions import db, limiter

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing credentials"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(username=data["username"])
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()

    user = User.query.filter_by(username=data.get("username")).first()

    if not user or not user.check_password(data.get("password")):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user.username)

    return jsonify({"access_token": token})
