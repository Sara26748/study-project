import os
from flask import Flask, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

bp = Blueprint("main", __name__)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    # Ensure the instance folder exists so SQLite can create the database file there
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # Add secret key for sessions
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "db.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)

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
    
    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
