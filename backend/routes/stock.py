from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models import db, StockItem, Movement

stock_bp = Blueprint("stock", __name__)

def serialize(item):
    return {
        "id": item.id, "name": item.name, "qty": item.qty,
        "unit": item.unit, "threshold": item.threshold, "category": item.category,
        "price": item.price or 0, "costPrice": item.cost_price or 0,
    }

@stock_bp.route("/api/stock/<category>", methods=["GET"])
@jwt_required()
def get_by_category(category):
    items = StockItem.query.filter_by(category=category).order_by(StockItem.name).all()
    return jsonify([serialize(i) for i in items])

@stock_bp.route("/api/stock", methods=["POST"])
@jwt_required()
def create():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Données requises"}), 400
    item = StockItem(
        name=data["name"], qty=data.get("qty", 0),
        unit=data["unit"], threshold=data.get("threshold", 0),
        category=data["category"],
        price=data.get("price", 0) or 0,
        cost_price=data.get("costPrice", 0) or 0,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(serialize(item)), 201

@stock_bp.route("/api/stock/<item_id>", methods=["PUT"])
@jwt_required()
def update(item_id):
    item = StockItem.query.get(item_id)
    if not item:
        return jsonify({"msg": "Article introuvable"}), 404
    data = request.get_json()
    for field in ("name", "qty", "unit", "threshold", "category", "price", "costPrice"):
        if field in data and data[field] is not None:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify(serialize(item))

@stock_bp.route("/api/stock/<item_id>", methods=["DELETE"])
@jwt_required()
def delete(item_id):
    item = StockItem.query.get(item_id)
    if not item:
        return jsonify({"msg": "Article introuvable"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"msg": "Article supprimé"})

# Mouvements de stock
@stock_bp.route("/api/stock/<item_id>/movement", methods=["POST"])
@jwt_required()
def add_movement(item_id):
    item = StockItem.query.get(item_id)
    if not item:
        return jsonify({"msg": "Article introuvable"}), 404
    data = request.get_json()
    mvt = Movement(
        item_id=item_id,
        type=data["type"],
        qty=data["qty"],
        note=data.get("note", "")
    )
    # Ajuster le stock
    if mvt.type == "entree":
        item.qty += mvt.qty
    elif mvt.type == "sortie":
        item.qty = max(0, item.qty - mvt.qty)

    db.session.add(mvt)
    db.session.commit()
    return jsonify({"msg": "Mouvement enregistré", "qty": item.qty}), 201

@stock_bp.route("/api/movements", methods=["GET"])
@jwt_required()
def get_movements():
    movements = Movement.query.order_by(Movement.date.desc()).limit(100).all()
    return jsonify([{
        "id": m.id, "itemId": m.item_id, "type": m.type,
        "qty": m.qty, "date": m.date.isoformat(), "note": m.note or ""
    } for m in movements])
