from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
from backend.models import db, User

users_bp = Blueprint("users", __name__)

def serialize(u):
    return {
        "id": u.id, "username": u.username,
        "role": u.role, "name": u.name
    }

@users_bp.route("/api/users", methods=["GET"])
@jwt_required()
def get_all():
    users = User.query.order_by(User.name).all()
    return jsonify([serialize(u) for u in users])

@users_bp.route("/api/users", methods=["POST"])
@jwt_required()
def create():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"msg": "Nom d'utilisateur déjà pris"}), 409
    user = User(
        username=data["username"],
        password=generate_password_hash(data["password"]),
        role=data.get("role", "reception"),
        name=data["name"]
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(serialize(user)), 201

@users_bp.route("/api/users/<user_id>", methods=["PUT"])
@jwt_required()
def update(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Utilisateur introuvable"}), 404
    data = request.get_json()
    if "name" in data:
        user.name = data["name"]
    if "role" in data:
        user.role = data["role"]
    if "password" in data and data["password"]:
        user.password = generate_password_hash(data["password"])
    db.session.commit()
    return jsonify(serialize(user))

@users_bp.route("/api/users/<user_id>", methods=["DELETE"])
@jwt_required()
def delete(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "Utilisateur introuvable"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "Utilisateur supprimé"})
