import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://betweenends:betweenends@localhost:5432/betweenends"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BETWEENENDS_API_BASE = os.environ.get(
        "BETWEENENDS_API_BASE", "https://resultsapi.herokuapp.com"
    )
    TOURNAMENT_CACHE_TTL_HOURS = int(os.environ.get("TOURNAMENT_CACHE_TTL_HOURS", "24"))
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin")
