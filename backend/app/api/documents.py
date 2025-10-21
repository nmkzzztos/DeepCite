from flask import Blueprint, send_file, current_app, jsonify
import os
import logging

from app.services.workspace_service import WorkspaceService
from app.logging_config import set_request_context, timing_logger

logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)

# Initialize services
workspace_service = WorkspaceService()

@documents_bp.route('/documents/<doc_id>/download', methods=['GET'])
@timing_logger('app.api.documents')
def download_document(doc_id):
    """Download the original PDF file for a document"""
    try:
        # Set request context for correlation
        import uuid
        request_id = str(uuid.uuid4())[:8]
        set_request_context(request_id)

        logger.info(f"DOCUMENT_DOWNLOAD_START: Starting download for document {doc_id}")

        # Get document from database
        from app.repositories.document_repository import DocumentRepository
        import os
        from flask import current_app

        doc_repo = DocumentRepository()
        document = doc_repo.get_by_id(doc_id)

        if not document:
            logger.warning(f"DOCUMENT_DOWNLOAD_ERROR: Document {doc_id} not found in database")
            return jsonify({'error': 'Document not found'}), 404

        file_path = document.file_path
        logger.info(f"DOCUMENT_DOWNLOAD_PATH: File path from DB: {file_path}")

        if not document.file_path or not os.path.exists(document.file_path):
            # Try to find file in different possible locations
            if not os.path.isabs(file_path):
                # If relative path, try relative to project root
                # current_app.root_path is backend/app, so go up two levels
                backend_dir = os.path.dirname(current_app.root_path)  # backend/
                project_root = os.path.dirname(backend_dir)  # project root
                file_path = os.path.join(project_root, file_path.lstrip('./'))
                logger.info(f"DOCUMENT_DOWNLOAD_PATH_CORRECTED: Trying corrected path: {file_path}")

            if not os.path.exists(file_path):
                logger.error(f"DOCUMENT_DOWNLOAD_FILE_NOT_FOUND: File not found at: {document.file_path} or {file_path}")
                return jsonify({'error': 'Document file not found on server'}), 404
        else:
            logger.info(f"DOCUMENT_DOWNLOAD_FILE_EXISTS: File exists at original path: {file_path}")

        # Get original filename from metadata
        filename = document.additional_metadata_dict.get('filename', f"{document.title}.pdf")
        logger.info(f"DOCUMENT_DOWNLOAD_FILENAME: Using filename: {filename}")

        # Send file for download - ensure absolute path
        abs_file_path = os.path.abspath(file_path)
        file_size = os.path.getsize(abs_file_path)
        logger.info(f"DOCUMENT_DOWNLOAD_SUCCESS: Sending file {abs_file_path} ({file_size} bytes)")

        return send_file(
            abs_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error downloading document {doc_id}: {e}")
        return jsonify({'error': str(e)}), 500


@documents_bp.route('/documents/<doc_id>/view', methods=['GET'])
@timing_logger('app.api.documents')
def view_document(doc_id):
    """Get document as base64 for frontend viewing"""
    try:
        # Set request context for correlation
        import uuid
        request_id = str(uuid.uuid4())[:8]
        set_request_context(request_id)

        logger.info(f"DOCUMENT_VIEW_START: Starting view for document {doc_id}")

        # Get document from database
        from app.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository()
        document = doc_repo.get_by_id(doc_id)

        if not document:
            logger.warning(f"DOCUMENT_VIEW_ERROR: Document {doc_id} not found in database")
            return jsonify({'error': 'Document not found'}), 404

        file_path = document.file_path
        logger.info(f"DOCUMENT_VIEW_PATH: File path from DB: {file_path}")

        if not document.file_path or not os.path.exists(document.file_path):
            # Try to find file in different possible locations
            if not os.path.isabs(file_path):
                # If relative path, try relative to project root
                # current_app.root_path is backend/app, so go up two levels
                backend_dir = os.path.dirname(current_app.root_path)  # backend/
                project_root = os.path.dirname(backend_dir)  # project root
                file_path = os.path.join(project_root, file_path.lstrip('./'))

            if not os.path.exists(file_path):
                logger.error(f"DOCUMENT_VIEW_FILE_NOT_FOUND: File not found at: {document.file_path} or {file_path}")
                return jsonify({'error': 'Document file not found on server'}), 404

        logger.info(f"DOCUMENT_VIEW_FILE_FOUND: File exists at: {file_path}")

        # Read file and encode as base64
        import base64
        logger.info(f"DOCUMENT_VIEW_READ_START: Reading file for base64 encoding")
        with open(file_path, 'rb') as f:
            file_content = f.read()

        logger.info(f"DOCUMENT_VIEW_READ_SUCCESS: Read file {file_path}, size: {len(file_content)} bytes")

        # Verify it's a PDF file
        if len(file_content) < 4 or file_content[:4] != b'%PDF':
            logger.error(f"DOCUMENT_VIEW_INVALID_PDF: File {file_path} is not a valid PDF (header: {file_content[:4]})")
            return jsonify({'error': 'File is not a valid PDF document'}), 400

        logger.info("DOCUMENT_VIEW_VALID_PDF: PDF validation passed")

        # Check file size - for very large files, suggest using download instead
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 5:  # More than 5MB
            logger.warning(f"DOCUMENT_VIEW_FILE_TOO_LARGE: File {file_path} is {file_size_mb:.2f}MB, suggesting download endpoint")
            return jsonify({
                'error': f'File too large for base64 encoding: {file_size_mb:.2f}MB. Use download endpoint instead.',
                'file_size': len(file_content),
                'use_download': True
            }), 413

        # Encode to base64
        logger.info("DOCUMENT_VIEW_ENCODING_START: Starting base64 encoding")
        base64_content = base64.b64encode(file_content).decode('utf-8')
        logger.info(f"DOCUMENT_VIEW_ENCODING_SUCCESS: Encoded to base64, length: {len(base64_content)} characters")

        # Validate base64
        if len(base64_content) % 4 != 0:
            logger.warning(f"DOCUMENT_VIEW_BASE64_WARNING: Base64 length {len(base64_content)} is not divisible by 4")

        # Get filename from metadata or default
        filename = document.additional_metadata_dict.get('filename', f"{document.title}.pdf")
        logger.info(f"DOCUMENT_VIEW_SUCCESS: Prepared document {doc_id} for viewing, filename: {filename}")

        return jsonify({
            'base64': base64_content,
            'filename': filename,
            'mimetype': 'application/pdf',
            'file_size': len(file_content)
        }), 200

    except Exception as e:
        logger.error(f"Error viewing document {doc_id}: {e}")
        return jsonify({'error': str(e)}), 500