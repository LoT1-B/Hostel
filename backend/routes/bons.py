from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime
from backend.models import db, Bon, User

bons_bp = Blueprint("bons", __name__)

def serialize(bon):
    try:
        import json as _json
        items = _json.loads(bon.items) if bon.items else []
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []
    return {
        "id": bon.id,
        "category": bon.category,
        "label": bon.label,
        "items": items,
        "montant": bon.montant,
        "cout": bon.cout,
        "status": bon.status,
        "day": bon.day.isoformat() if bon.day else None,
        "createdAt": bon.created_at.isoformat() if bon.created_at else None,
        "createdBy": bon.created_by or "",
        "encaisseAt": bon.encaisse_at.isoformat() if bon.encaisse_at else None,
        "encaisseBy": bon.encaisse_by or "",
    }

def parse_day(value):
    """Accepte YYYY-MM-DD ou une date ISO complète."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None

@bons_bp.route("/api/bons", methods=["GET"])
@jwt_required()
def list_bons():
    q = Bon.query
    day = parse_day(request.args.get("day"))
    status = request.args.get("status")
    if day:
        q = q.filter(Bon.day == day)
    if status:
        q = q.filter(Bon.status == status)
    bons = q.order_by(Bon.created_at.desc()).all()
    return jsonify([serialize(b) for b in bons])

@bons_bp.route("/api/bons/summary", methods=["GET"])
@jwt_required()
def bons_summary():
    day = parse_day(request.args.get("day")) or date.today()
    bons = Bon.query.filter(Bon.day == day).all()
    encaisses = [b for b in bons if b.status == "encaisse"]
    en_attente = [b for b in bons if b.status == "ouvert"]
    total_encaisse = sum(b.montant or 0 for b in encaisses)
    total_cout = sum(b.cout or 0 for b in encaisses)
    total_en_attente = sum(b.montant or 0 for b in en_attente)
    return jsonify({
        "day": day.isoformat(),
        "totalEncaisse": total_encaisse,
        "totalCout": total_cout,
        "benefice": total_encaisse - total_cout,
        "nbEncaisses": len(encaisses),
        "nbEnAttente": len(en_attente),
        "totalEnAttente": total_en_attente,
    })

@bons_bp.route("/api/bons", methods=["POST"])
@jwt_required()
def create_bon():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400

    category = data.get("category", "")
    if category not in ("boisson", "nourriture"):
        return jsonify({"msg": "Catégorie invalide (boisson ou nourriture)"}), 400
    label = (data.get("label") or "").strip()
    if not label:
        return jsonify({"msg": "La description du bon est requise"}), 400

    try:
        montant = int(data.get("montant", 0) or 0)
        cout = int(data.get("cout", 0) or 0)
    except (TypeError, ValueError):
        return jsonify({"msg": "Montant invalide"}), 400
    if montant < 0 or cout < 0:
        return jsonify({"msg": "Montant invalide"}), 400

    day = parse_day(data.get("day"))
    if not day:
        return jsonify({"msg": "Date du bon invalide"}), 400

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    created_by = user.username if user else data.get("createdBy", "")

    # Idempotence : si le client fournit son propre id, on le respecte
    existing = None
    client_id = data.get("id")
    if client_id:
        existing = Bon.query.get(client_id)
        if existing:
            return jsonify(serialize(existing)), 200

    items = data.get("items")
    if items is None:
        items = "[]"
    elif not isinstance(items, str):
        try:
            import json as _json
            items = _json.dumps(items, ensure_ascii=False)
        except Exception:
            items = "[]"

    bon = Bon(
        id=client_id or None,
        category=category, label=label, items=items,
        montant=montant, cout=cout,
        status=data.get("status", "ouvert"),
        day=day,
        created_by=created_by,
    )
    if bon.status == "encaisse":
        bon.encaisse_at = datetime.utcnow()
        bon.encaisse_by = created_by

    db.session.add(bon)
    db.session.commit()
    return jsonify(serialize(bon)), 201

@bons_bp.route("/api/bons/<bon_id>", methods=["PUT"])
@jwt_required()
def update_bon(bon_id):
    bon = Bon.query.get(bon_id)
    if not bon:
        return jsonify({"msg": "Bon introuvable"}), 404
    data = request.get_json() or {}

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    username = user.username if user else data.get("encaisseBy", "")

    if "status" in data and data["status"] != bon.status:
        bon.status = data["status"]
        if data["status"] == "encaisse":
            bon.encaisse_at = datetime.utcnow()
            bon.encaisse_by = username
        elif data["status"] in ("ouvert", "annule"):
            bon.encaisse_at = None
            bon.encaisse_by = ""

    for field in ("label", "category", "montant", "cout"):
        if field in data and data[field] is not None:
            setattr(bon, field, data[field])
    if "day" in data:
        d = parse_day(data["day"])
        if d:
            bon.day = d
    if "items" in data:
        items = data["items"]
        if not isinstance(items, str):
            try:
                import json as _json
                items = _json.dumps(items, ensure_ascii=False)
            except Exception:
                items = "[]"
        bon.items = items

    db.session.commit()
    return jsonify(serialize(bon))

@bons_bp.route("/api/bons/<bon_id>", methods=["DELETE"])
@jwt_required()
def delete_bon(bon_id):
    bon = Bon.query.get(bon_id)
    if not bon:
        return jsonify({"msg": "Bon introuvable"}), 404
    db.session.delete(bon)
    db.session.commit()
    return jsonify({"msg": "Bon supprimé"})
