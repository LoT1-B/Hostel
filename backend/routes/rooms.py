from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from backend.models import db, Room, Reservation

rooms_bp = Blueprint("rooms", __name__)

@rooms_bp.route("/api/rooms", methods=["GET"])
@jwt_required()
def get_rooms():
    rooms = Room.query.order_by(Room.number).all()
    return jsonify([{
        "id": r.id, "number": r.number, "name": r.name or "", "type": r.type,
        "price": r.price, "status": r.status
    } for r in rooms])

@rooms_bp.route("/api/rooms/<room_id>", methods=["GET"])
@jwt_required()
def get_room(room_id):
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"msg": "Chambre introuvable"}), 404
    return jsonify({
        "id": r.id, "number": r.number, "name": r.name or "", "type": r.type,
        "price": r.price, "status": r.status
    })

@rooms_bp.route("/api/rooms", methods=["POST"])
@jwt_required()
def create_room():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400
    room = Room(
        number=data["number"], name=data.get("name", ""), type=data["type"],
        price=data["price"], status=data.get("status", "available")
    )
    db.session.add(room)
    db.session.commit()
    return jsonify({"id": room.id, "number": room.number, "name": room.name or "",
                    "type": room.type, "price": room.price, "status": room.status}), 201

@rooms_bp.route("/api/rooms/<room_id>", methods=["PUT"])
@jwt_required()
def update_room(room_id):
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"msg": "Chambre introuvable"}), 404
    data = request.get_json()
    for field in ("number", "name", "type", "price", "status"):
        if field in data:
            setattr(r, field, data[field])
    db.session.commit()
    return jsonify({"id": r.id, "number": r.number, "name": r.name or "",
                    "type": r.type, "price": r.price, "status": r.status})

@rooms_bp.route("/api/rooms/<room_id>", methods=["DELETE"])
@jwt_required()
def delete_room(room_id):
    r = Room.query.get(room_id)
    if not r:
        return jsonify({"msg": "Chambre introuvable"}), 404
    active = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(["pending", "checked-in"]),
    ).all()
    if active:
        return jsonify({"msg": "Chambre avec des réservations actives. Annulez ou libérez d'abord."}), 409
    # Supprimer l'historique (terminé/annulé) lié à la chambre, sinon la FK bloque le DELETE
    for res in Reservation.query.filter(Reservation.room_id == room_id).all():
        db.session.delete(res)
    db.session.delete(r)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Impossible de supprimer : données liées."}), 409
    return jsonify({"msg": "Chambre supprimée"})
