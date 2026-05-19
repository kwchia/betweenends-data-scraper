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
    ARCHER_SCAN_RECENT_YEARS = int(os.environ.get("ARCHER_SCAN_RECENT_YEARS", "3"))
    ARCHER_SCAN_BATCH_COMMIT_EVERY = int(os.environ.get("ARCHER_SCAN_BATCH_COMMIT_EVERY", "10"))
    ARCHER_MEMBERSHIP_API_FIELDS = [
        f.strip()
        for f in os.environ.get(
            "ARCHER_MEMBERSHIP_API_FIELDS", "mid,mem,usaid,aid_ext,member_id,membership"
        ).split(",")
        if f.strip()
    ]
    GUNICORN_WORKERS = int(os.environ.get("GUNICORN_WORKERS", "2"))
    GUNICORN_TIMEOUT = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    ARCHER_SCAN_QUEUE_NAME = os.environ.get("ARCHER_SCAN_QUEUE_NAME", "archer-scans")
    ARCHER_SCAN_JOB_TIMEOUT = int(os.environ.get("ARCHER_SCAN_JOB_TIMEOUT", "600"))
