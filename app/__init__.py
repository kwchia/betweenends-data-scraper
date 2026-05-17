from flask import Flask

from app.config import Config
from app.extensions import db, login_manager, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.cli import ensure_admin_command

    app.cli.add_command(ensure_admin_command)

    from app.blueprints.auth import auth_bp
    from app.blueprints.library import library_bp
    from app.blueprints.profile import profile_bp
    from app.blueprints.tournaments import tournaments_bp
    from app.services import result_summaries

    app.jinja_env.globals.update(
        division_summary=result_summaries.summarize_division,
        archer_summary=result_summaries.summarize_archer,
        match_summary=result_summaries.summarize_match,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tournaments_bp)

    @app.route("/")
    def root():
        from flask import redirect, url_for

        return redirect(url_for("tournaments.index"))

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
