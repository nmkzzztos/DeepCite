"""
Chat API endpoints for DeepCite
"""
import logging
import uuid
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any
import markdown2
from concurrent.futures import ThreadPoolExecutor
import functools

from app.models.ai_models import (
    ChatMessage, ChatConversation, ModelConfig,
    get_generation_models, get_model_info
)
from app.services.llm.model_provider_manager import get_model_provider_manager
from app.services.rag_service import RAGService
from app.logging_config import set_request_context, timing_logger

logger = logging.getLogger(__name__)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=10)

def run_async(func):
    """Decorator to run async functions in Flask"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is already running, use thread pool
            future = executor.submit(asyncio.run, func(*args, **kwargs))
            return future.result()
        else:
            return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/models', methods=['GET'])
@run_async
async def get_available_models():
    """Get list of available generation models"""
    try:
        models = get_generation_models()
        return jsonify({
            'success': True,
            'models': [
                {
                    'id': model.id,
                    'name': model.name,
                    'provider': model.provider,
                    'description': model.description,
                    'max_completion_tokens': model.max_completion_tokens,
                    'supports_streaming': model.supports_streaming
                }
                for model in models
            ]
        })
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/send', methods=['POST'])
@run_async
@timing_logger('app.api.chat')
async def send_message():
    """Send a message to the AI model and get response"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'message' not in data or 'model_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: message, model_id'
            }), 400
        
        message = data['message']
        model_id = data['model_id']
        conversation_history = data.get('conversation_history', [])
        request_id = data.get('request_id', str(uuid.uuid4()))
        selected_workspaces = data.get('selected_workspaces', [])
        selected_documents = data.get('selected_documents', {})
        chat_mode = data.get('chat_mode', 'normal')
        selected_domains = data.get('selected_domains', [])

        # Set request context for correlation
        set_request_context(request_id)

        logger.info(f"CHAT_REQUEST_START: Processing request for model {model_id}, mode: {chat_mode}")
        logger.info(f"CHAT_REQUEST_DATA: Workspaces: {len(selected_workspaces)}, Documents: {sum(len(docs) for docs in selected_documents.values())}")
        logger.info(f"CHAT_REQUEST_DATA: Message length: {len(message)} chars, History: {len(conversation_history)} messages")
        
        # Validate model exists and check compatibility with chat mode
        model_info = get_model_info(model_id)
        if not model_info:
            return jsonify({
                'success': False,
                'error': f'Model {model_id} not found'
            }), 400

        # For internet mode, ensure we're using a compatible model (Perplexity)
        if chat_mode == 'internet' and model_info.provider != 'perplexity':
            logger.warning(f"Internet mode requested but non-Perplexity model {model_id} selected. This may not work as expected.")
        
        # Check if we need to perform RAG search
        context = ""
        search_results = []
        
        if selected_workspaces or selected_documents:
            logger.info(f"RAG_SEARCH_START: Performing search for query (length: {len(message)} chars)")

            # Flatten selected documents into a single list
            document_ids = []
            for workspace_docs in selected_documents.values():
                document_ids.extend(workspace_docs)

            logger.info(f"RAG_SEARCH_PARAMS: Workspaces: {selected_workspaces}, Document IDs: {document_ids}")

            # Use RAG service to search for relevant content
            rag_service = RAGService()
            context, search_results = rag_service.search_and_generate_context(
                query=message,
                workspace_ids=selected_workspaces if selected_workspaces else None,
                document_ids=document_ids if document_ids else None,
                max_results=20,
                max_context_length=4000
            )

            logger.info(f"RAG_SEARCH_RESULTS: Found {len(search_results)} results, context length: {len(context)} chars")

            # If no search results but workspaces/documents were selected, inform the user
            if not search_results and (selected_workspaces or selected_documents):
                logger.warning("RAG_SEARCH_WARNING: No search results found despite workspace/document selection")
                context = "Note: You have selected specific workspaces/documents for this query, but no relevant content was found in those sources. This could mean the documents are still being processed or don't contain information relevant to your question.\n\n"
        
        # Build messages for the AI model
        messages = []
        
        # Add system prompt for markdown formatting and RAG context
        system_prompt = 'You are a helpful AI assistant. Format your responses using markdown syntax for better readability (headers, lists, latex in $$ ... $$ or $ ... $, etc.).'
        
        if context:
            system_prompt += '\n\nYou have access to relevant document passages that will be provided in the user message. Use this information to provide accurate, well-sourced answers.'
        
        messages.append({
            'role': 'system',
            'content': system_prompt
        })
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Add current user message with context if available
        user_message = message
        if context:
            user_message = f"{context}\n\nUser Question: {message}"
        
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        # Get model provider manager
        provider_manager = get_model_provider_manager()
        
        # Generate response using the provider manager
        try:
            # Prepare additional parameters based on chat mode
            generate_kwargs = {}

            # Set max completion tokens if provided
            if data.get('max_completion_tokens'):
                generate_kwargs['max_completion_tokens'] = data.get('max_completion_tokens')

            # Add Perplexity-specific parameters for internet mode
            if chat_mode == 'internet' and selected_domains:
                generate_kwargs['custom_domains'] = selected_domains
                logger.info(f"MODEL_GENERATION_PARAMS: Using custom domains for internet search: {selected_domains}")

            logger.info(f"MODEL_GENERATION_START: Calling {model_id} with {len(messages)} messages")
            result = await provider_manager.generate(
                messages=messages,
                model_id=model_id,
                **generate_kwargs
            )
            result_text = result.text if hasattr(result, 'text') else str(result)
            logger.info(f"MODEL_GENERATION_SUCCESS: Generated response of {len(result_text)} characters")
        except Exception as provider_error:
            logger.error(f"MODEL_GENERATION_ERROR: Provider manager failed: {str(provider_error)}")
            # Fallback to mock response if provider manager fails
            result_text = f"This is a mock response from {model_id} for: {message}"
            result = None
            logger.info("MODEL_GENERATION_FALLBACK: Using mock response")
        
        # Convert markdown to HTML using markdown2
        html_content = markdown2.markdown(result_text, extras=['tables', 'lists', 'latex', 'fenced-code-blocks'])
        
        return jsonify({
            'success': True,
            'response': {
                'content': result_text,
                'html_content': html_content,
                'model': model_id,
                'usage': result.usage if result and hasattr(result, 'usage') else {'total_tokens': 0},
                'timestamp': datetime.now().isoformat(),
                'request_id': request_id,
            'search_results': search_results if search_results else [],
            'formatted_citations': result.metadata.get('formatted_citations', []) if result and hasattr(result, 'metadata') else [],
            'citations': result.metadata.get('citations', []) if result and hasattr(result, 'metadata') else [],
            'context_used': bool(context)
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/health', methods=['GET'])
@run_async
async def chat_health():
    """Check chat service health"""
    try:
        provider_manager = get_model_provider_manager()
        health_status = await provider_manager.health_check_all()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'providers': health_status
        })
    except Exception as e:
        logger.error(f"Chat health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@chat_bp.route('/test-rag', methods=['POST'])
def test_rag():
    """Test RAG functionality"""
    try:
        data = request.get_json()
        query = data.get('query', 'test query')
        workspace_ids = data.get('workspace_ids', [])
        document_ids = data.get('document_ids', [])
        
        rag_service = RAGService()
        search_results = rag_service.search_documents(
            query=query,
            workspace_ids=workspace_ids,
            document_ids=document_ids,
            max_results=5
        )
        
        return jsonify({
            'success': True,
            'query': query,
            'workspace_ids': workspace_ids,
            'document_ids': document_ids,
            'results_count': len(search_results),
            'results': search_results
        })
    except Exception as e:
        logger.error(f"RAG test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500