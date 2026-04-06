from flask import Flask
from .config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from .extensions import db, migrate, jwt, cors, limiter, talisman, admin, celery

def create_app(config_name='development'):
    app = Flask(__name__)

    if config_name == 'development':
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'production':
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        app.config.from_object(TestingConfig)
    else:
        app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, supports_credentials=True)
    limiter.init_app(app)
    if app.config.get('TALISMAN_ENABLED', True):
        talisman.init_app(app, content_security_policy=None)
    admin.init_app(app)

    app.url_map.strict_slashes = False

    with app.app_context():
        from . import models

    from .api.auth import auth_bp
    from .api.tracks import tracks_bp
    from .api.playlists import playlists_bp
    from .api.social import social_bp
    from .api.user import user_bp
    from .api.admin import admin_bp as admin_api_bp
    from .api.artists import artists_bp
    from .api.genres import genres_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tracks_bp, url_prefix='/api/tracks')
    app.register_blueprint(playlists_bp, url_prefix='/api/playlists')
    app.register_blueprint(social_bp, url_prefix='/api/social')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
    app.register_blueprint(artists_bp, url_prefix='/api/artists')
    app.register_blueprint(genres_bp, url_prefix='/api/genres')

    from .frontend import frontend
    app.register_blueprint(frontend, url_prefix='/')

    celery.conf.update(app.config)

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app