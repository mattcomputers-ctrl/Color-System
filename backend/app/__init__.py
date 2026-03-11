import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True)

    # CSRF protection — exempt the API blueprint since it uses JWT
    csrf.init_app(app)

    # Configure logging
    _configure_logging(app)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.series import series_bp
    from app.api.bases import bases_bp
    from app.api.pantone import pantone_bp
    from app.api.custom_match import custom_match_bp
    from app.api.admin import admin_bp
    from app.api.export import export_bp

    api_prefix = '/api/v1'
    app.register_blueprint(auth_bp, url_prefix=f'{api_prefix}/auth')
    app.register_blueprint(series_bp, url_prefix=f'{api_prefix}/series')
    app.register_blueprint(bases_bp, url_prefix=f'{api_prefix}/bases')
    app.register_blueprint(pantone_bp, url_prefix=f'{api_prefix}/pantone')
    app.register_blueprint(custom_match_bp, url_prefix=f'{api_prefix}/custom-match')
    app.register_blueprint(admin_bp, url_prefix=f'{api_prefix}/admin')
    app.register_blueprint(export_bp, url_prefix=f'{api_prefix}/export')

    # Exempt API blueprints from CSRF (they use JWT)
    for bp in [auth_bp, series_bp, bases_bp, pantone_bp, custom_match_bp, admin_bp, export_bp]:
        csrf.exempt(bp)

    return app


def _configure_logging(app):
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    app.logger.addHandler(stream_handler)

    # File handler (if configured)
    log_file = app.config.get('LOG_FILE')
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10_000_000, backupCount=10
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(log_level)
