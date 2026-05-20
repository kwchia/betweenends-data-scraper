"""App mode: club coach vs individual (my results)."""

from flask import session
from flask_login import current_user

MODE_CLUB = "club"
MODE_ARCHER = "archer"


def get_app_mode() -> str:
    mode = session.get("app_mode")
    if mode in (MODE_CLUB, MODE_ARCHER):
        return mode
    if current_user.is_authenticated and current_user.preferred_mode in (
        MODE_CLUB,
        MODE_ARCHER,
    ):
        return current_user.preferred_mode
    return MODE_CLUB


def set_app_mode(mode: str) -> None:
    if mode not in (MODE_CLUB, MODE_ARCHER):
        mode = MODE_CLUB
    session["app_mode"] = mode
    if current_user.is_authenticated:
        current_user.preferred_mode = mode


def is_archer_mode() -> bool:
    return get_app_mode() == MODE_ARCHER
