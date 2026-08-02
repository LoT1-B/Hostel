from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import uuid

db = SQLAlchemy()

def gen_id():
    return uuid.uuid4().hex[:12]

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashé
    role = db.Column(db.String(20), nullable=False, default="reception")
    name = db.Column(db.String(100), nullable=False)

class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    number = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), default="")  # nom de la chambre (ex: Orchidée)
    type = db.Column(db.String(30), nullable=False)  # Simple, Suite, Deluxe
    price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="available")  # available, occupied, maintenance
    archived = db.Column(db.Boolean, default=False)  # soft delete : garde l'historique des résas

class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    guest = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.String(12), db.ForeignKey("rooms.id"), nullable=False)
    room_number = db.Column(db.String(100), nullable=False)
    checkin = db.Column(db.Date, nullable=False)
    checkout = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, checked-in, checked-out, cancelled
    notes = db.Column(db.Text, default="")

class StockItem(db.Model):
    __tablename__ = "stock_items"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    name = db.Column(db.String(100), nullable=False)
    qty = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False)
    threshold = db.Column(db.Float, nullable=False, default=0)
    category = db.Column(db.String(20), nullable=False)  # boisson, nourriture
    price = db.Column(db.Integer, default=0)          # prix de vente unitaire (caisse)
    cost_price = db.Column(db.Integer, default=0)     # prix d'achat unitaire (bénéfice)

class Movement(db.Model):
    __tablename__ = "movements"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    item_id = db.Column(db.String(12), db.ForeignKey("stock_items.id"), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # entree, sortie
    qty = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200), default="")

class Bon(db.Model):
    __tablename__ = "bons"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    category = db.Column(db.String(20), nullable=False)  # boisson, nourriture
    label = db.Column(db.String(200), nullable=False)
    items = db.Column(db.Text, default="[]")             # JSON des lignes (stockItemId, name, qty, unitPrice, unitCost)
    montant = db.Column(db.Integer, nullable=False, default=0)
    cout = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), default="ouvert")  # ouvert, encaisse, annule
    day = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), default="")
    encaisse_at = db.Column(db.DateTime, nullable=True)
    encaisse_by = db.Column(db.String(50), default="")

class ClosedDay(db.Model):
    __tablename__ = "closed_days"
    id = db.Column(db.String(12), primary_key=True, default=gen_id)
    day = db.Column(db.Date, nullable=False, unique=True)
    closed_at = db.Column(db.DateTime, nullable=False)
    rooms_total = db.Column(db.Integer, default=0)
    occupied = db.Column(db.Integer, default=0)
    occupancy_rate = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Integer, default=0)
    arrivals = db.Column(db.Integer, default=0)
    departures = db.Column(db.Integer, default=0)
    boisson_entrees = db.Column(db.Float, default=0)
    boisson_sorties = db.Column(db.Float, default=0)
    nourriture_entrees = db.Column(db.Float, default=0)
    nourriture_sorties = db.Column(db.Float, default=0)
    low_stock_count = db.Column(db.Integer, default=0)
    caisse_encaisse = db.Column(db.Integer, default=0)
    caisse_cout = db.Column(db.Integer, default=0)
    caisse_benefice = db.Column(db.Integer, default=0)
    locked = db.Column(db.Boolean, default=False)
    closed_by = db.Column(db.String(12), db.ForeignKey("users.id"), nullable=True)

class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200), nullable=False)
