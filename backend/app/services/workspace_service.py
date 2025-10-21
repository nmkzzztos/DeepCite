"""
Workspace service for managing document collections
"""
import os
import logging
from typing import List, Optional, Dict, Any
from werkzeug.datastructures import FileStorage
from flask import current_app

from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion.document_ingestion_service import DocumentIngestionService
from app.models.workspace import Workspace
from app.models.document import Document
from app import db

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service for workspace operations"""
    
    def __init__(self):
        self.workspace_repo = WorkspaceRepository()
        self.document_repo = DocumentRepository()
        # Enable embeddings for RAG functionality
        self.ingestion_service = DocumentIngestionService(enable_embeddings=True)
    
    def get_all_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces with document counts"""
        workspaces = self.workspace_repo.get_all()
        return [self._workspace_to_dict(workspace) for workspace in workspaces]
    
    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by ID with documents"""
        workspace = self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            return None
        
        workspace_dict = self._workspace_to_dict(workspace)
        # Add documents with processing status
        workspace_dict['documents'] = [
            self._document_to_dict(doc) for doc in workspace.documents
        ]
        
        return workspace_dict
    
    def create_workspace(self, name: str, description: str = None) -> Optional[Dict[str, Any]]:
        """Create a new workspace"""
        workspace = self.workspace_repo.create(name, description)
        if not workspace:
            return None
        
        return self._workspace_to_dict(workspace)
    
    def update_workspace(self, workspace_id: str, name: str = None, description: str = None) -> Optional[Dict[str, Any]]:
        """Update workspace"""
        workspace = self.workspace_repo.update(workspace_id, name, description)
        if not workspace:
            return None
        
        return self._workspace_to_dict(workspace)
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete workspace and all associated data.

        This includes:
        - Documents that are only in this workspace (with their files, paragraphs, embeddings)
        - Workspace-document associations
        - The workspace itself

        Args:
            workspace_id: Workspace ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get workspace
            workspace = self.workspace_repo.get_by_id(workspace_id)
            if not workspace:
                logger.warning(f"Workspace {workspace_id} not found for deletion")
                return False

            # Get all documents in this workspace
            documents_to_check = workspace.documents[:]

            # For each document, check if it exists in other workspaces
            for document in documents_to_check:
                other_workspaces_count = len([
                    w for w in document.workspaces
                    if str(w.workspace_id) != workspace_id
                ])

                if other_workspaces_count == 0:
                    # Document is only in this workspace, delete it completely
                    logger.info(f"Document {document.doc_id} is only in workspace {workspace_id}, deleting completely")
                    success = self.ingestion_service.delete_document(str(document.doc_id))
                    if not success:
                        logger.error(f"Failed to delete document {document.doc_id}")
                        # Continue with other documents, don't fail the whole operation
                else:
                    # Document exists in other workspaces, just remove from this workspace
                    logger.info(f"Document {document.doc_id} exists in {other_workspaces_count} other workspaces, removing association only")
                    self.workspace_repo.remove_document(workspace_id, str(document.doc_id))

            # Delete workspace (this will also remove remaining associations via cascade if configured)
            success = self.workspace_repo.delete(workspace_id)

            if success:
                logger.info(f"Successfully deleted workspace {workspace_id} and all associated data")
            else:
                logger.error(f"Failed to delete workspace {workspace_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting workspace {workspace_id}: {e}")
            return False
    
    def upload_document(self, workspace_id: str, file: FileStorage, metadata: Dict[str, Any] = None, embedding_model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload and process a document for a workspace
        
        Args:
            workspace_id: Target workspace ID
            file: Uploaded file
            metadata: Optional metadata override
            embedding_model_id: Optional embedding model ID to use
            
        Returns:
            Dictionary with upload result
        """
        try:
            # Validate workspace exists
            workspace = self.workspace_repo.get_by_id(workspace_id)
            if not workspace:
                return {
                    'success': False,
                    'error': 'Workspace not found'
                }
            
            # Validate file
            if not file or not file.filename:
                return {
                    'success': False,
                    'error': 'No file provided'
                }
            
            if not file.filename.lower().endswith('.pdf'):
                return {
                    'success': False,
                    'error': 'Only PDF files are supported'
                }
            
            # Read file content
            file_content = file.read()
            if not file_content:
                return {
                    'success': False,
                    'error': 'Empty file'
                }

            # Add filename and file size to metadata
            if not metadata:
                metadata = {}
            metadata['filename'] = file.filename
            metadata['file_size'] = len(file_content)

            # Process document with ingestion service
            logger.info(f"Starting document ingestion for {file.filename} in workspace {workspace_id}")

            result = self.ingestion_service.ingest_document_from_bytes(
                file_content,
                metadata_override=metadata,
                embedding_model_id=embedding_model_id
            )

            # Save original file to disk after getting doc_id
            if result and result.success and result.doc_id:
                import os
                from werkzeug.utils import secure_filename
                from flask import current_app

                upload_folder = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)

                # Create unique filename using actual doc_id
                safe_filename = secure_filename(file.filename)
                unique_filename = f"{result.doc_id}_{safe_filename}"
                file_path = os.path.join(upload_folder, unique_filename)

                # Save file to disk
                with open(file_path, 'wb') as f:
                    f.write(file_content)

                # Update document with file path
                if result.document:
                    result.document.file_path = file_path
                    db.session.commit()
                    logger.info(f"Updated document {result.doc_id} with file path: {file_path}")


            if not result or not result.success:
                error_msg = result.error_message if result else 'Document processing failed'
                logger.error(f"Document ingestion failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Add document to workspace
            if not self.workspace_repo.add_document(workspace_id, result.doc_id):
                logger.error(f"Failed to add document {result.doc_id} to workspace {workspace_id}")
                # Document was processed but not added to workspace
                # Could clean up here, but for now just log the error
                return {
                    'success': False,
                    'error': 'Failed to add document to workspace'
                }
            
            logger.info(f"Successfully uploaded and processed document {result.doc_id} for workspace {workspace_id}")
            
            return {
                'success': True,
                'doc_id': result.doc_id,
                'document': self._document_to_dict(result.document) if result.document else None,
                'paragraphs_count': result.paragraphs_count,
                'processing_time': result.processing_time_seconds
            }
            
        except Exception as e:
            logger.error(f"Error uploading document to workspace {workspace_id}: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def remove_document(self, workspace_id: str, doc_id: str) -> bool:
        """Remove document from workspace"""
        return self.workspace_repo.remove_document(workspace_id, doc_id)
    
    def delete_document(self, workspace_id: str, doc_id: str) -> bool:
        """Delete document completely (from all workspaces and database)"""
        try:
            # Remove from workspace first
            self.workspace_repo.remove_document(workspace_id, doc_id)
            
            # Check if document is in other workspaces
            document = self.document_repo.get_by_id(doc_id)
            if document and len(document.workspaces) == 0:
                # Document not in any workspace, safe to delete completely
                return self.ingestion_service.delete_document(doc_id)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} from workspace {workspace_id}: {e}")
            return False
    
    def get_workspace_documents(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all documents in a workspace"""
        documents = self.workspace_repo.get_documents(workspace_id)
        return [self._document_to_dict(doc) for doc in documents]
    
    def _workspace_to_dict(self, workspace: Workspace) -> Dict[str, Any]:
        """Convert workspace model to dictionary"""
        return {
            'id': workspace.workspace_id,
            'name': workspace.name,
            'description': workspace.description,
            'documentCount': len(workspace.documents),
            'embeddingCount': len(workspace.embeddings),
            'paragraphCount': len(workspace.paragraphs),
            'createdAt': workspace.created_at.isoformat() if workspace.created_at else None,
            'updatedAt': workspace.updated_at.isoformat() if workspace.updated_at else None
        }
    
    def _document_to_dict(self, document: Document) -> Dict[str, Any]:
        """Convert document model to dictionary with processing status"""
        doc_dict = document.to_dict()
        
        # Add processing status based on paragraphs and embeddings
        paragraph_count = len(document.paragraphs)
        embedding_count = sum(len(p.embeddings) for p in document.paragraphs)
        
        if paragraph_count == 0:
            processing_status = 'failed'
        elif embedding_count == 0:
            processing_status = 'processing'
        else:
            processing_status = 'completed'
        
        # Add frontend-compatible fields
        doc_dict.update({
            'id': document.doc_id,
            'filename': document.additional_metadata_dict.get('filename', document.title),
            'processingStatus': processing_status,
            'uploadedAt': document.added_at.isoformat() if document.added_at else None,
            'fileSize': document.additional_metadata_dict.get('file_size', 0),
            'pageCount': document.additional_metadata_dict.get('page_count', 0),
            'paragraphCount': paragraph_count,
            'embeddingCount': embedding_count
        })
        
        return doc_dict