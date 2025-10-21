from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import logging

from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)
workspaces_bp = Blueprint('workspaces', __name__)

# Initialize services
workspace_service = WorkspaceService()

def get_embedding_service():
    """Get embedding service instance (lazy initialization)"""
    from app.services.embedding_service import EmbeddingService
    return EmbeddingService()

@workspaces_bp.route('/workspaces', methods=['GET'])
def get_workspaces():
    """Get all workspaces"""
    try:
        workspaces = workspace_service.get_all_workspaces()
        return jsonify({
            'workspaces': workspaces,
            'total': len(workspaces)
        }), 200
    except Exception as e:
        logger.error(f"Error getting workspaces: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/workspaces', methods=['POST'])
def create_workspace():
    """Create a new workspace"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Workspace name is required'}), 400
        
        workspace = workspace_service.create_workspace(
            name=data['name'],
            description=data.get('description', '')
        )
        
        if not workspace:
            return jsonify({'error': 'Failed to create workspace'}), 500
        
        return jsonify(workspace), 201
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/workspaces/<workspace_id>', methods=['GET'])
def get_workspace(workspace_id):
    """Get a specific workspace"""
    try:
        workspace = workspace_service.get_workspace(workspace_id)
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        return jsonify(workspace), 200
    except Exception as e:
        logger.error(f"Error getting workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/workspaces/<workspace_id>', methods=['DELETE'])
def delete_workspace(workspace_id):
    """Delete a workspace"""
    try:
        success = workspace_service.delete_workspace(workspace_id)
        
        if not success:
            return jsonify({'error': 'Workspace not found or could not be deleted'}), 404
        
        return jsonify({'message': 'Workspace deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/workspaces/<workspace_id>', methods=['PUT'])
def update_workspace(workspace_id):
    """Update a workspace"""
    try:
        data = request.get_json()
        
        workspace = workspace_service.update_workspace(
            workspace_id=workspace_id,
            name=data.get('name'),
            description=data.get('description')
        )
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        return jsonify(workspace), 200
    except Exception as e:
        logger.error(f"Error updating workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/workspaces/<workspace_id>/documents', methods=['POST'])
def upload_document(workspace_id):
    """Upload a document to a workspace"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get optional metadata from form data
        metadata = {}
        if 'title' in request.form:
            metadata['title'] = request.form['title']
        if 'authors' in request.form:
            # Parse authors as JSON array or comma-separated string
            authors_str = request.form['authors']
            try:
                import json
                metadata['authors'] = json.loads(authors_str)
            except:
                # Fallback to comma-separated
                metadata['authors'] = [a.strip() for a in authors_str.split(',') if a.strip()]
        if 'year' in request.form:
            try:
                metadata['year'] = int(request.form['year'])
            except ValueError:
                pass
        if 'source' in request.form:
            metadata['source'] = request.form['source']
        
        # Get embedding model selection
        embedding_model_id = request.form.get('embedding_model_id')
        
        # Upload and process document
        result = workspace_service.upload_document(workspace_id, file, metadata, embedding_model_id)
        
        if not result['success']:
            return jsonify({'error': result['error']}), 400
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error uploading document to workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500


@workspaces_bp.route('/workspaces/<workspace_id>/documents', methods=['GET'])
def get_workspace_documents(workspace_id):
    """Get all documents in a workspace"""
    try:
        documents = workspace_service.get_workspace_documents(workspace_id)
        return jsonify({
            'documents': documents,
            'total': len(documents)
        }), 200
    except Exception as e:
        logger.error(f"Error getting documents for workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500


@workspaces_bp.route('/workspaces/<workspace_id>/documents/<doc_id>', methods=['DELETE'])
def delete_document(workspace_id, doc_id):
    """Delete a document from workspace"""
    try:
        # Check if we should delete completely or just remove from workspace
        delete_completely = request.args.get('delete_completely', 'false').lower() == 'true'
        
        if delete_completely:
            success = workspace_service.delete_document(workspace_id, doc_id)
        else:
            success = workspace_service.remove_document(workspace_id, doc_id)
        
        if not success:
            return jsonify({'error': 'Document not found or could not be deleted'}), 404
        
        return jsonify({'message': 'Document deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting document {doc_id} from workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500


@workspaces_bp.route('/workspaces/<workspace_id>/documents/<doc_id>/remove', methods=['POST'])
def remove_document_from_workspace(workspace_id, doc_id):
    """Remove a document from workspace (but keep in database)"""
    try:
        success = workspace_service.remove_document(workspace_id, doc_id)
        
        if not success:
            return jsonify({'error': 'Document not found or could not be removed'}), 404
        
        return jsonify({'message': 'Document removed from workspace'}), 200
    except Exception as e:
        logger.error(f"Error removing document {doc_id} from workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500


@workspaces_bp.route('/embedding-models', methods=['GET'])
def get_embedding_models():
    """Get available embedding models"""
    try:
        embedding_service = get_embedding_service()
        models = embedding_service.get_available_embedding_models()
        default_model = embedding_service.get_default_embedding_model()
        
        return jsonify({
            'models': [model.to_dict() for model in models],
            'default': default_model
        }), 200
    except Exception as e:
        logger.error(f"Error getting embedding models: {e}")
        return jsonify({'error': str(e)}), 500


@workspaces_bp.route('/embedding-stats', methods=['GET'])
def get_embedding_stats():
    """Get embedding statistics"""
    try:
        embedding_service = get_embedding_service()
        stats = embedding_service.get_embedding_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting embedding stats: {e}")
        return jsonify({'error': str(e)}), 500