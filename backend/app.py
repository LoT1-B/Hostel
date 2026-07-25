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

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # Create tables and seed
    with app.app_context():
        db.create_all()
        seed_demo_data()

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
