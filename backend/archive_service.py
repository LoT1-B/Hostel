# backend/archive_service.py
"""Garde-fou d'archivage mensuel + construction des snapshots.

Le principe : un mois archivé (status='frozen') devient lecture seule.
Toute écriture qui touche une entité datée de ce mois est refusée (409).
"""
import json
from datetime import date, datetime, timedelta

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from backend.models import (
    db, Archive, Reservation, Room, Bon, ClosedDay, Movement, StockItem, User,
)


def month_key(d):
    return d.strftime("%Y-%m") if d else None


def next_month_first(month):
    """Retourne la date du 1er du mois suivant 'YYYY-MM'."""
    y, m = int(month[:4]), int(month[5:7])
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


def _get(month):
    return Archive.query.filter_by(month=month).first()


def is_frozen(month):
    a = _get(month)
    return bool(a and a.status == "frozen")


def current_user():
    return User.query.get(get_jwt_identity())


def guard(month, code=409):
    """Retourne une réponse Flask de refus si le mois est FIGE, sinon None."""
    if is_frozen(month):
        return jsonify({
            "msg": f"Le mois {month} est archivé et figé : plus aucune modification possible."
                    " Ré-ouvrez-le (manager) pour corriger."
        }), code
    return None


def guard_date(d, code=409):
    return guard(month_key(d), code) if d else None


def _iso_serialize(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


def build_snapshot(month):
    """Copie JSON complète des données appartenant à ce mois (données figées)."""
    first = date(int(month[:4]), int(month[5:7]), 1)
    last = next_month_first(month)
    end = last - timedelta(days=1)

    resas = Reservation.query.filter(
        Reservation.checkin >= first, Reservation.checkin < last
    ).order_by(Reservation.checkin).all()

    bons = Bon.query.filter(
        Bon.day >= first, Bon.day < last
    ).order_by(Bon.day).all()

    closed = ClosedDay.query.filter(
        ClosedDay.day >= first, ClosedDay.day < last
    ).order_by(ClosedDay.day).all()

    moves = Movement.query.filter(
        Movement.date >= datetime.combine(first, datetime.min.time()),
        Movement.date < datetime.combine(last, datetime.min.time()),
    ).order_by(Movement.date).all()
    item_name = {i.id: i.name for i in StockItem.query.all()}

    items = StockItem.query.order_by(StockItem.name).all()

    bons_enc = [b for b in bons if b.status == "encaisse"]
    bons_ouverts = [b for b in bons if b.status == "ouvert"]

    def mov_dict(m):
        return {
            "type": m.type, "qty": m.qty, "item": item_name.get(m.item_id, ""),
            "date": m.date.isoformat() if m.date else None, "note": m.note or "",
        }

    def bon_dict(b):
        import json as _j
        try:
            lines = _j.loads(b.items) if b.items else []
            if not isinstance(lines, list):
                lines = []
        except Exception:
            lines = []
        return {
            "id": b.id, "category": b.category, "label": b.label, "lines": lines,
            "montant": b.montant, "cout": b.cout, "status": b.status,
            "day": b.day.isoformat() if b.day else None,
            "createdBy": b.created_by or "",
        }

    def resa_dict(r):
        return {
            "guest": r.guest, "room": r.room_number, "checkin": r.checkin.isoformat(),
            "checkout": r.checkout.isoformat(), "status": r.status, "notes": r.notes or "",
        }

    def closed_dict(c):
        return {
            "day": c.day.isoformat(), "occupied": c.occupied, "rooms_total": c.rooms_total,
            "occupancy_rate": c.occupancy_rate, "revenue": c.revenue,
            "arrivals": c.arrivals, "departures": c.departures,
            "boisson_entrees": c.boisson_entrees, "boisson_sorties": c.boisson_sorties,
            "nourriture_entrees": c.nourriture_entrees, "nourriture_sorties": c.nourriture_sorties,
            "low_stock_count": c.low_stock_count,
            "caisse_encaisse": c.caisse_encaisse, "caisse_cout": c.caisse_cout,
            "caisse_benefice": c.caisse_benefice,
        }

    return {
        "month": month,
        "period": f"du {first.isoformat()} au {end.isoformat()}",
        "statistics": {
            "jour_ingenie": len(closed),
            "reservations": len(resas),
            "bons": len(bons),
            "bons_encaisse": len(bons_enc),
            "bons_ouverts": len(bons_ouverts),
            "caisse_encaisse": sum(b.montant or 0 for b in bons_enc),
            "caisse_benefice": sum((b.montant or 0) - (b.cout or 0) for b in bons_enc),
            "revenues_journalieres": sum(c.revenue or 0 for c in closed),
            "mouvements": len(moves),
            "nb_chambres_a_la_fin": len(items),
            "stock_final_qty": sum(i.qty or 0 for i in items),
        },
        "reservations": [resa_dict(r) for r in resas],
        "bons": [bon_dict(b) for b in bons],
        "closed_days": [closed_dict(c) for c in closed],
        "movements": [mov_dict(m) for m in moves],
        "stock_final": [{
            "name": i.name, "qty": i.qty, "unit": i.unit,
            "category": i.category, "threshold": i.threshold,
        } for i in items],
        "archived_at": datetime.utcnow().isoformat(),
    }


def get_roles_allowed():
    return None


def is_manager_user(user):
    return bool(user and user.role == "manager")