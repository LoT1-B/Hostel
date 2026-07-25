from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from models import db, User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400

    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter(db.func.lower(User.username) == username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "Identifiant ou mot de passe incorrect"}), 401

    token = create_access_token(identity=user.id)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role, "name": user.name}
    }), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Utilisateur introuvable"}), 404
    return jsonify({"id": user.id, "username": user.username, "role": user.role, "name": user.name})
