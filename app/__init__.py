import os
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from config import Config
from app.models import db, User, Notification

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Also ensure images directory exists for static assets
    os.makedirs(os.path.join(app.root_path, 'static', 'images'), exist_ok=True)

    # Register Blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Inject contextual helpers into all templates
    @app.context_processor
    def inject_globals():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()
        return {
            'unread_notifications_count': unread_count,
            'CATEGORIES': Config.CATEGORIES,
            'current_year': 2026
        }

    # Automatically initialize tables if needed
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database schema auto-creation notice: {e}")

    return app
