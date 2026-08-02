from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import date, datetime
from backend.models import db, Reservation, Room
from backend.archive_service import guard_date

reservations_bp = Blueprint("reservations", __name__)

def serialize(r):
    return {
        "id": r.id, "guest": r.guest, "roomNumber": r.room_number,
        "roomId": r.room_id,
        "checkin": r.checkin.isoformat(), "checkout": r.checkout.isoformat(),
        "status": r.status, "notes": r.notes or ""
    }

@reservations_bp.route("/api/reservations", methods=["GET"])
@jwt_required()
def get_all():
    reservations = Reservation.query.order_by(Reservation.checkin.desc()).all()
    return jsonify([serialize(r) for r in reservations])

@reservations_bp.route("/api/reservations/<res_id>", methods=["GET"])
@jwt_required()
def get_one(res_id):
    r = Reservation.query.get(res_id)
    if not r:
        return jsonify({"msg": "Réservation introuvable"}), 404
    return jsonify(serialize(r))

@reservations_bp.route("/api/reservations", methods=["POST"])
@jwt_required()
def create():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400

    # Vérifier la chambre
    room = Room.query.get(data["roomId"])
    if not room:
        return jsonify({"msg": "Chambre introuvable"}), 404

    checkin = date.fromisoformat(data["checkin"])
    checkout = date.fromisoformat(data["checkout"])
    # Un mois archivé/figé est lecture seule : interdire d'y créer une réservation
    resp = guard_date(checkin)
    if resp:
        return resp

    res = Reservation(
        guest=data["guest"], room_id=room.id, room_number=room.number,
        checkin=checkin,
        checkout=checkout,
        status=data.get("status", "pending"),
        notes=data.get("notes", "")
    )
    db.session.add(res)

    # Mettre à jour le statut de la chambre
    if res.status in ("checked-in",):
        room.status = "occupied"
    db.session.commit()
    return jsonify(serialize(res)), 201

@reservations_bp.route("/api/reservations/<res_id>", methods=["PUT"])
@jwt_required()
def update(res_id):
    r = Reservation.query.get(res_id)
    if not r:
        return jsonify({"msg": "Réservation introuvable"}), 404
    data = request.get_json()

    # Si la réservation (ou son checkin) tombe dans un mois archivé → refus
    resp = guard_date(r.checkin)
    if resp:
        return resp
    if "checkin" in data and data["checkin"]:
        resp = guard_date(date.fromisoformat(data["checkin"]))
        if resp:
            return resp

    old_status = r.status
    for field in ("guest", "notes", "status"):
        if field in data:
            setattr(r, field, data[field])
    if "checkin" in data:
        r.checkin = date.fromisoformat(data["checkin"])
    if "checkout" in data:
        r.checkout = date.fromisoformat(data["checkout"])

    # Gestion des changements de statut
    room = Room.query.get(r.room_id)
    if room:
        if r.status == "checked-in" and old_status != "checked-in":
            room.status = "occupied"
        elif r.status in ("checked-out", "cancelled") and room.status == "occupied":
            # Vérifier s'il y a d'autres réservations actives
            other_active = Reservation.query.filter(
                Reservation.room_id == r.room_id,
                Reservation.status == "checked-in",
                Reservation.id != r.id
            ).first()
            if not other_active:
                room.status = "available"

    db.session.commit()
    return jsonify(serialize(r))

@reservations_bp.route("/api/reservations/<res_id>", methods=["DELETE"])
@jwt_required()
def delete(res_id):
    r = Reservation.query.get(res_id)
    if not r:
        return jsonify({"msg": "Réservation introuvable"}), 404
    resp = guard_date(r.checkin)
    if resp:
        return resp
    db.session.delete(r)
    db.session.commit()
    return jsonify({"msg": "Réservation supprimée"})