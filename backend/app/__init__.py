# DeepCite Backend Application
import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Disable Flask's default logging immediately
    app.logger.disabled = True
    
    # Load configuration from config class
    from app.config import config
    config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Setup logging (this will re-enable app.logger with our config)
    from app.logging_config import setup_logging
    setup_logging(app)
    
    # Initialize model provider system
    from app.services.llm.model_provider_manager import initialize_model_provider_manager
    try:
        # Get the config instance to access the property
        config_instance = config[config_name]()
        model_config = config_instance.MODEL_PROVIDERS_CONFIG
        model_manager = initialize_model_provider_manager(model_config)
        app.model_provider_manager = model_manager
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Initialized model providers: {model_manager.get_available_providers()}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize model providers: {e}")
        # Continue without model providers for now
        app.model_provider_manager = None
    
    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    return app