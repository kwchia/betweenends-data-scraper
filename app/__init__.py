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

    from app.blueprints.archer import archer_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.library import library_bp
    from app.blueprints.profile import profile_bp
    from app.blueprints.tournaments import tournaments_bp
    from app.mode import get_app_mode
    from app.services import result_summaries
    from app.services.archer_metadata import get_round_metadata
    from app.services.summary import medal_highlights_by_tier

    app.jinja_env.globals.update(
        division_summary=result_summaries.summarize_division,
        archer_summary=result_summaries.summarize_archer,
        match_summary=result_summaries.summarize_match,
        round_metadata=get_round_metadata,
        medal_highlights_by_tier=medal_highlights_by_tier,
    )

    @app.context_processor
    def inject_app_mode():
        return {"app_mode": get_app_mode()}

    app.register_blueprint(auth_bp)
    app.register_blueprint(archer_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(tournaments_bp)

    @app.route("/")
    def root():
        from flask import redirect, url_for

        from app.mode import is_archer_mode

        if is_archer_mode():
            return redirect(url_for("archer.library"))
        return redirect(url_for("tournaments.index"))

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
