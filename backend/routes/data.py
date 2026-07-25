from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
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
    q = ClosedDay.query

    # Filtre par plage de dates
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    if start:
        q = q.filter(ClosedDay.day >= datetime.strptime(start, "%Y-%m-%d").date())
    if end:
        q = q.filter(ClosedDay.day <= datetime.strptime(end, "%Y-%m-%d").date())

    days = q.order_by(ClosedDay.day.desc()).all()
    return jsonify([{
        "day": d.day.isoformat(), "closedAt": d.closed_at.isoformat() if d.closed_at else None,
        "roomsTotal": d.rooms_total, "occupied": d.occupied,
        "occupancyRate": d.occupancy_rate, "revenue": d.revenue,
        "arrivals": d.arrivals, "departures": d.departures,
        "boissonEntrees": d.boisson_entrees, "boissonSorties": d.boisson_sorties,
        "nourritureEntrees": d.nourriture_entrees, "nourritureSorties": d.nourriture_sorties,
        "lowStockCount": d.low_stock_count,
        "locked": d.locked,
        "closedBy": d.closed_by,
    } for d in days])

@data_bp.route("/api/closed-days", methods=["POST"])
@jwt_required()
def close_day():
    """Ferme la journée courante — irréversible."""
    from flask_jwt_extended import get_jwt_identity
    from backend.models import User

    user_id = get_jwt_identity()
    # Récupérer le nom d'utilisateur qui ferme
    closing_user = User.query.get(user_id)
    closed_by_username = closing_user.username if closing_user else 'inconnu'
    today = date.today()

    existing = ClosedDay.query.filter_by(day=today).first()
    if existing:
        if existing.locked:
            return jsonify({"msg": "Journée déjà clôturée et verrouillée"}), 409
        # Si non verrouillée, on peut la remplacer (manager seulement)
        db.session.delete(existing)
        db.session.commit()

    rooms = Room.query.count()
    occupied = Reservation.query.filter(Reservation.status == "checked-in").count()
    arrivals = Reservation.query.filter(Reservation.checkin == today).count()
    departures = Reservation.query.filter(Reservation.checkout == today).count()
    low_stock = StockItem.query.filter(StockItem.qty <= StockItem.threshold).count()

    closed = ClosedDay(
        day=today, closed_at=datetime.utcnow(),
        rooms_total=rooms, occupied=occupied,
        occupancy_rate=round((occupied / rooms * 100)) if rooms else 0,
        revenue=occupied * 20000,
        arrivals=arrivals, departures=departures,
        boisson_entrees=0, boisson_sorties=0,
        nourriture_entrees=0, nourriture_sorties=0,
        low_stock_count=low_stock,
        locked=True,                    # ← verrouillé immédiatement
        closed_by=closed_by_username,
    )
    db.session.add(closed)
    db.session.commit()
    return jsonify({"msg": "Journée clôturée", "day": today.isoformat()}), 201

# ——— ALERTES STOCK ———
@data_bp.route("/api/stock/alerts", methods=["GET"])
@jwt_required()
def stock_alerts():
    """Retourne les articles en dessous du seuil d'alerte."""
    items = StockItem.query.filter(StockItem.qty <= StockItem.threshold).all()
    return jsonify([{
        "id": i.id, "name": i.name,
        "qty": i.qty, "unit": i.unit,
        "threshold": i.threshold,
        "category": i.category,
    } for i in items])

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
