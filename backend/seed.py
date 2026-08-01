from backend.models import db, User, Room, Reservation, StockItem, Movement, ClosedDay, Setting
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

def seed_demo_data():
    """Initialise les données de démonstration."""
    if User.query.first():
        return  # Déjà initialisé

    # Settings
    db.session.add(Setting(key="hotelName", value="Villa Blanca"))
    db.session.add(Setting(key="dayBoundary", value="midnight"))

    # Users
    users = [
        User(username="manager", password=generate_password_hash("manager123"), role="manager", name="Manager"),
        User(username="reception", password=generate_password_hash("reception123"), role="reception", name="Réceptionniste"),
    ]
    db.session.add_all(users)

    # Rooms
    rooms = [
        Room(number="101", name="Orchidée", type="Simple", price=15000, status="available"),
        Room(number="102", name="Ambre", type="Simple", price=15000, status="occupied"),
        Room(number="201", name="Océan", type="Suite", price=35000, status="available"),
        Room(number="202", name="Lagon", type="Suite", price=35000, status="available"),
        Room(number="301", name="Royale", type="Deluxe", price=50000, status="maintenance"),
    ]
    db.session.add_all(rooms)
    db.session.flush()

    # Reservation
    today = date.today()
    res = Reservation(
        guest="K. Amouzou", room_id=rooms[1].id, room_number="102",
        checkin=today, checkout=today + timedelta(2),
        status="checked-in", notes=""
    )
    db.session.add(res)

    # Stock
    boissons = [
        StockItem(name="Eau minérale", qty=60, unit="bouteilles", threshold=20, category="boisson", price=1000, cost_price=600),
        StockItem(name="Bière (Awooyo)", qty=8, unit="casiers", threshold=10, category="boisson", price=1200, cost_price=700),
        StockItem(name="Sodas", qty=30, unit="bouteilles", threshold=15, category="boisson", price=900, cost_price=500),
    ]
    nourritures = [
        StockItem(name="Riz", qty=25, unit="kg", threshold=10, category="nourriture"),
        StockItem(name="Poulet", qty=4, unit="kg", threshold=5, category="nourriture"),
        StockItem(name="Légumes", qty=12, unit="kg", threshold=8, category="nourriture"),
    ]
    db.session.add_all(boissons + nourritures)

    # Closed days (historique 3 jours)
    for offset in [3, 2, 1]:
        day = today - timedelta(offset)
        db.session.add(ClosedDay(
            day=day,
            closed_at=datetime(day.year, day.month, day.day, 22, 0),
            rooms_total=len(rooms),
            occupied=2 + (offset % 2),
            occupancy_rate=round(((2 + (offset % 2)) / len(rooms)) * 100),
            revenue=30000 + offset * 5000,
            arrivals=1,
            departures=1 if offset == 2 else 0,
            boisson_entrees=0,
            boisson_sorties=10 + offset,
            nourriture_entrees=5,
            nourriture_sorties=6 + offset,
            low_stock_count=1 if offset == 3 else 0,
        ))

    db.session.commit()
