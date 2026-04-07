import os

from flask import Flask

from app.config import config
from app.extensions import db, limiter, login_manager, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Set Cloud SQL engine options for production
    if os.environ.get("CLOUD_SQL_INSTANCE"):
        from app.config import _make_cloud_sql_creator

        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "creator": _make_cloud_sql_creator()
        }

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)

    # Jinja filters — `markdown_safe` renders AI-generated markdown text into
    # safe HTML for both the website and the WeasyPrint PDF templates.
    from app.services.markdown_renderer import render_markdown_safe
    app.jinja_env.filters["markdown_safe"] = render_markdown_safe

    # Register user_loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.assessment import assessment_bp
    from app.documents import documents_bp
    from app.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(dashboard_bp)

    # Create tables on startup if they don't exist (production)
    if config_name == "production":
        with app.app_context():
            db.create_all()

    return app
