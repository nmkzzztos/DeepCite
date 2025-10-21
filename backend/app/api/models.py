"""
API endpoints for AI model management
"""
import asyncio
import logging
from flask import Blueprint, jsonify, request
from app.services.llm.model_provider_manager import get_model_provider_manager

logger = logging.getLogger(__name__)

models_bp = Blueprint('models', __name__, url_prefix='/models')

@models_bp.route('/', methods=['GET'])
def list_models():
    """List all available AI models from all providers"""
    try:
        manager = get_model_provider_manager()
        models = asyncio.run(manager.list_all_models())
        
        return jsonify({
            'success': True,
            'models': [
                {
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'type': model.type.value,
                    'capabilities': model.capabilities,
                    'context_length': model.context_length,
                    'max_output_tokens': model.max_output_tokens
                }
                for model in models
            ]
        })
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/providers', methods=['GET'])
def list_providers():
    """List all available AI providers"""
    try:
        manager = get_model_provider_manager()
        providers = manager.get_available_providers()
        
        return jsonify({
            'success': True,
            'providers': providers
        })
    except Exception as e:
        logger.error(f"Error listing providers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/health', methods=['GET'])
def health_check():
    """Check health status of all AI providers"""
    try:
        manager = get_model_provider_manager()
        health_status = asyncio.run(manager.health_check_all())
        
        return jsonify({
            'success': True,
            'health': health_status
        })
    except Exception as e:
        logger.error(f"Error checking provider health: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@models_bp.route('/providers/<provider_name>/models', methods=['GET'])
def list_provider_models(provider_name):
    """List models for a specific provider"""
    try:
        manager = get_model_provider_manager()
        provider = manager.get_provider(provider_name)
        
        if not provider:
            return jsonify({
                'success': False,
                'error': f'Provider {provider_name} not found'
            }), 404
        
        models = asyncio.run(provider.list_models())
        
        return jsonify({
            'success': True,
            'provider': provider_name,
            'models': [
                {
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'type': model.type.value,
                    'capabilities': model.capabilities,
                    'context_length': model.context_length,
                    'max_output_tokens': model.max_output_tokens
                }
                for model in models
            ]
        })
    except Exception as e:
        logger.error(f"Error listing models for provider {provider_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500