import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.models import User


def ensure_default_admin() -> None:
    admin_email = current_app.config.get("DEFAULT_ADMIN_EMAIL", "admin")
    admin_password = current_app.config.get("DEFAULT_ADMIN_PASSWORD", "admin")

    if User.query.filter_by(email=admin_email).first():
        return

    user = User(email=admin_email)
    user.set_password(admin_password)
    db.session.add(user)
    db.session.commit()


@click.command("ensure-admin")
@with_appcontext
def ensure_admin_command():
    """Create the default admin account if it does not exist."""
    ensure_default_admin()
    email = current_app.config.get("DEFAULT_ADMIN_EMAIL", "admin")
    click.echo(f"Default admin account ready (login: {email})")
