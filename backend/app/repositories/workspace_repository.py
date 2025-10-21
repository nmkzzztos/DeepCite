"""
Repository for workspace data access
"""
from typing import List, Optional
from app import db
from app.models.workspace import Workspace
from app.models.document import Document
import logging

logger = logging.getLogger(__name__)


class WorkspaceRepository:
    """Repository for workspace operations"""
    
    def get_all(self) -> List[Workspace]:
        """Get all workspaces"""
        try:
            return Workspace.query.all()
        except Exception as e:
            logger.error(f"Error getting all workspaces: {e}")
            return []
    
    def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID"""
        try:
            return Workspace.query.filter_by(workspace_id=workspace_id).first()
        except Exception as e:
            logger.error(f"Error getting workspace {workspace_id}: {e}")
            return None
    
    def create(self, name: str, description: str = None) -> Optional[Workspace]:
        """Create a new workspace"""
        try:
            workspace = Workspace(
                name=name,
                description=description
            )
            db.session.add(workspace)
            db.session.commit()
            logger.info(f"Created workspace {workspace.workspace_id}: {name}")
            return workspace
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            db.session.rollback()
            return None
    
    def update(self, workspace_id: str, name: str = None, description: str = None) -> Optional[Workspace]:
        """Update workspace"""
        try:
            workspace = self.get_by_id(workspace_id)
            if not workspace:
                return None
            
            if name is not None:
                workspace.name = name
            if description is not None:
                workspace.description = description
            
            db.session.commit()
            logger.info(f"Updated workspace {workspace_id}")
            return workspace
        except Exception as e:
            logger.error(f"Error updating workspace {workspace_id}: {e}")
            db.session.rollback()
            return None
    
    def delete(self, workspace_id: str) -> bool:
        """Delete workspace"""
        try:
            workspace = self.get_by_id(workspace_id)
            if not workspace:
                return False
            
            db.session.delete(workspace)
            db.session.commit()
            logger.info(f"Deleted workspace {workspace_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting workspace {workspace_id}: {e}")
            db.session.rollback()
            return False
    
    def add_document(self, workspace_id: str, doc_id: str) -> bool:
        """Add document to workspace"""
        try:
            workspace = self.get_by_id(workspace_id)
            document = Document.query.filter_by(doc_id=doc_id).first()
            
            if not workspace or not document:
                return False
            
            if document not in workspace.documents:
                workspace.documents.append(document)
                db.session.commit()
                logger.info(f"Added document {doc_id} to workspace {workspace_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error adding document {doc_id} to workspace {workspace_id}: {e}")
            db.session.rollback()
            return False
    
    def remove_document(self, workspace_id: str, doc_id: str) -> bool:
        """Remove document from workspace"""
        try:
            workspace = self.get_by_id(workspace_id)
            document = Document.query.filter_by(doc_id=doc_id).first()
            
            if not workspace or not document:
                return False
            
            if document in workspace.documents:
                workspace.documents.remove(document)
                db.session.commit()
                logger.info(f"Removed document {doc_id} from workspace {workspace_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error removing document {doc_id} from workspace {workspace_id}: {e}")
            db.session.rollback()
            return False
    
    def get_documents(self, workspace_id: str) -> List[Document]:
        """Get all documents in workspace"""
        try:
            workspace = self.get_by_id(workspace_id)
            if not workspace:
                return []
            return workspace.documents
        except Exception as e:
            logger.error(f"Error getting documents for workspace {workspace_id}: {e}")
            return []