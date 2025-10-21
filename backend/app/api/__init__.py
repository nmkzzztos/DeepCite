# API endpoints
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import modules to register their routes
from . import documents
from .chat import chat_bp
from .workspaces import workspaces_bp
from .papers import papers_bp

# Import and register model blueprint
from .models import models_bp

# Register blueprints
api_bp.register_blueprint(chat_bp, url_prefix='/chat')
api_bp.register_blueprint(models_bp)
api_bp.register_blueprint(workspaces_bp)
api_bp.register_blueprint(documents.documents_bp)
api_bp.register_blueprint(papers_bp, url_prefix='/papers')