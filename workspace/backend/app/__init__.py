from flask import Flask
from .config import Config
from .extensions import db, jwt, migrate, limiter
from .auth import auth_bp
from .routes import routes_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    return app
