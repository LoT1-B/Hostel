import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config import Config
from backend.models import db
from backend.routes.auth import auth_bp
from backend.routes.rooms import rooms_bp
from backend.routes.reservations import reservations_bp
from backend.routes.stock import stock_bp
from backend.routes.users import users_bp
from backend.routes.data import data_bp
from backend.routes.bons import bons_bp
from backend.seed import seed_demo_data

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    CORS(app, resources={r"/api/*": {
        "origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "https://lot1-b.github.io",
            "https://hostel-2v4z.onrender.com"
        ]
    }})
    db.init_app(app)
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(bons_bp)

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # Create tables and seed
    with app.app_context():
        db.create_all()
        _migrate(app)
        seed_demo_data()

    return app


def _migrate(app):
    """Migrations légères : ajoute les colonnes manquantes sur les tables existantes."""
    from sqlalchemy import inspect, text
    with app.app_context():
        insp = inspect(db.engine)
        # Postgres exige DEFAULT false pour un BOOLEAN (SQLite tolère 0)
        bool_default = "false" if db.engine.dialect.name == "postgresql" else "0"
        for table, cols in {
            "closed_days": {
                "caisse_encaisse": "INTEGER DEFAULT 0",
                "caisse_cout": "INTEGER DEFAULT 0",
                "caisse_benefice": "INTEGER DEFAULT 0",
            },
            "stock_items": {
                "price": "INTEGER DEFAULT 0",
                "cost_price": "INTEGER DEFAULT 0",
            },
            "rooms": {
                "name": "VARCHAR(100) DEFAULT ''",
                "archived": f"BOOLEAN DEFAULT {bool_default}",
            },
        }.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col, sql in cols.items():
                if col not in existing:
                    db.session.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {sql}"
                    ))
        db.session.commit()
        _backfill_prices()
        _backfill_room_names()


def _backfill_room_names():
    """Base existante : donne un nom aux chambres démo qui n'en ont pas (aligné sur le front)."""
    from sqlalchemy import text
    defaults = {
        "101": "Orchidée", "102": "Ambre", "201": "Océan", "202": "Lagon", "301": "Royale",
    }
    for number, name in defaults.items():
        db.session.execute(text(
            "UPDATE rooms SET name=:n WHERE number=:num AND (name IS NULL OR name = '')"
        ), {"n": name, "num": number})
    db.session.commit()


def _backfill_prices():
    """Base existante : les articles démo n'ont pas de prix → on les remplit une seule fois (si jamais mis)."""
    from sqlalchemy import text
    defaults = {
        "Eau minérale": (1000, 600),
        "Bière (Awooyo)": (1200, 700),
        "Sodas": (900, 500),
    }
    for name, (price, cost) in defaults.items():
        db.session.execute(text(
            "UPDATE stock_items SET price=:p, cost_price=:c WHERE name=:n AND (price IS NULL OR price = 0)"
        ), {"p": price, "c": cost, "n": name})
    db.session.commit()

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
