from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import date, datetime
from backend.models import db, ClosedDay, Room, Reservation, StockItem, Setting

data_bp = Blueprint("data", __name__)

@data_bp.route("/api/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    today = date.today()
    rooms = Room.query.count()
    active_rs = Reservation.query.filter(
        Reservation.status == "checked-in"
    ).count()
    arrivals_today = Reservation.query.filter(
        Reservation.checkin == today
    ).count()
    departures_today = Reservation.query.filter(
        Reservation.checkout == today
    ).count()
    low_stock = StockItem.query.filter(
        StockItem.qty <= StockItem.threshold
    ).count()

    return jsonify({
        "rooms_total": rooms,
        "occupied": active_rs,
        "occupancy_rate": round((active_rs / rooms * 100)) if rooms else 0,
        "arrivals": arrivals_today,
        "departures": departures_today,
        "low_stock_count": low_stock,
    })

@data_bp.route("/api/closed-days", methods=["GET"])
@jwt_required()
def get_closed_days():
    days = ClosedDay.query.order_by(ClosedDay.day.desc()).all()
    return jsonify([{
        "day": d.day.isoformat(), "closedAt": d.closed_at.isoformat(),
        "roomsTotal": d.rooms_total, "occupied": d.occupied,
        "occupancyRate": d.occupancy_rate, "revenue": d.revenue,
        "arrivals": d.arrivals, "departures": d.departures,
        "boissonEntrees": d.boisson_entrees, "boissonSorties": d.boisson_sorties,
        "nourritureEntrees": d.nourriture_entrees, "nourritureSorties": d.nourriture_sorties,
        "lowStockCount": d.low_stock_count,
    } for d in days])

@data_bp.route("/api/closed-days", methods=["POST"])
@jwt_required()
def close_day():
    """Ferme la journée courante et calcule les stats."""
    today = date.today()
    if ClosedDay.query.filter_by(day=today).first():
        return jsonify({"msg": "Jour déjà clôturé"}), 409

    rooms = Room.query.count()
    occupied = Reservation.query.filter(Reservation.status == "checked-in").count()
    arrivals = Reservation.query.filter(Reservation.checkin == today).count()
    departures = Reservation.query.filter(Reservation.checkout == today).count()
    low_stock = StockItem.query.filter(StockItem.qty <= StockItem.threshold).count()

    closed = ClosedDay(
        day=today, closed_at=datetime.utcnow(),
        rooms_total=rooms, occupied=occupied,
        occupancy_rate=round((occupied / rooms * 100)) if rooms else 0,
        revenue=occupied * 20000,  # estimation simplifiée
        arrivals=arrivals, departures=departures,
        boisson_entrees=0, boisson_sorties=0,
        nourriture_entrees=0, nourriture_sorties=0,
        low_stock_count=low_stock,
    )
    db.session.add(closed)
    db.session.commit()
    return jsonify({"msg": "Journée clôturée", "day": today.isoformat()}), 201

# Settings
@data_bp.route("/api/settings", methods=["GET"])
def get_settings():
    settings = Setting.query.all()
    result = {s.key: s.value for s in settings}
    return jsonify(result)

@data_bp.route("/api/settings", methods=["PUT"])
@jwt_required()
def update_settings():
    data = request.get_json()
    for key, value in data.items():
        s = Setting.query.get(key)
        if s:
            s.value = str(value)
        else:
            db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()
    return jsonify({"msg": "Paramètres mis à jour"})
