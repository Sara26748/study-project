import os
from flask import Flask, Blueprint, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_babel import Babel, get_locale

bp = Blueprint("main", __name__)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
babel = Babel()

def create_app():
    app = Flask(__name__)
    # Ensure the instance folder exists so SQLite can create the database file there
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # Add secret key for sessions
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "db.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['BABEL_DEFAULT_LOCALE'] = 'de'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['de', 'en', 'fr', 'es']
    db.init_app(app)
    migrate.init_app(app, db)

    def select_locale():
        lang = session.get('lang')
        supported = app.config.get('BABEL_SUPPORTED_LOCALES', [])
        if lang in supported:
            return lang
        return request.accept_languages.best_match(supported) or app.config.get('BABEL_DEFAULT_LOCALE', 'de')

    babel.init_app(app, locale_selector=select_locale)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from . import models
    # db.create_all() nicht mehr automatisch, da Migrationen verwendet werden

    from .routes import bp
    from .auth import auth_bp
    from .agent import agent_bp
    app.register_blueprint(bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(agent_bp)

    from .migration import migration_bp
    app.register_blueprint(migration_bp)

    @app.context_processor
    def inject_locale():
        language_options = [
            {"code": "de", "label": "Deutsch", "flag": "de"},
            {"code": "en", "label": "English", "flag": "gb"},
            {"code": "fr", "label": "Français", "flag": "fr"},
            {"code": "es", "label": "Español", "flag": "es"},
        ]
        return {
            "current_locale": str(get_locale() or "de"),
            "language_options": language_options,
        }
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
