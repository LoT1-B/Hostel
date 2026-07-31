import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "villa-blanca-secret-key-2026")
    _db_url = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'villa_blanca.db')}"
    )
    # Render/Neon exposent des URLs "postgres://" — SQLAlchemy 2 exige "postgresql://"
    if _db_url.startswith("postgres://"):
        _db_url = "postgresql://" + _db_url[len("postgres://"):]
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-villa-2026")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24h
