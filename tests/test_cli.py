from app.models import User


def test_ensure_admin_creates_user(app):
    with app.app_context():
        from flask.cli import ScriptInfo
        from app.cli import ensure_admin_command

        runner = app.test_cli_runner()
        result = runner.invoke(ensure_admin_command)
        assert result.exit_code == 0

        user = User.query.filter_by(email="admin").first()
        assert user is not None
        assert user.check_password("admin")

        # Idempotent
        result2 = runner.invoke(ensure_admin_command)
        assert result2.exit_code == 0
        assert User.query.filter_by(email="admin").count() == 1
