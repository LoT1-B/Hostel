import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.rooms import rooms_bp
from routes.reservations import reservations_bp
from routes.stock import stock_bp
from routes.users import users_bp
from routes.data import data_bp
from seed import seed_demo_data

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
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
