"""
Repository for document data access
"""
from typing import List, Optional
from app import db
from app.models.document import Document
import logging

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document operations"""
    
    def get_all(self) -> List[Document]:
        """Get all documents"""
        try:
            return Document.query.all()
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return []
    
    def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        try:
            return Document.query.filter_by(doc_id=doc_id).first()
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    def get_by_sha256(self, sha256: str) -> Optional[Document]:
        """Get document by SHA256 hash"""
        try:
            return Document.query.filter_by(sha256=sha256).first()
        except Exception as e:
            logger.error(f"Error getting document by hash {sha256}: {e}")
            return None
    
    def create(self, **kwargs) -> Optional[Document]:
        """Create a new document"""
        try:
            document = Document(**kwargs)
            db.session.add(document)
            db.session.commit()
            logger.info(f"Created document {document.doc_id}: {document.title}")
            return document
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            db.session.rollback()
            return None
    
    def update(self, doc_id: str, **kwargs) -> Optional[Document]:
        """Update document"""
        try:
            document = self.get_by_id(doc_id)
            if not document:
                return None
            
            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            db.session.commit()
            logger.info(f"Updated document {doc_id}")
            return document
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            db.session.rollback()
            return None
    
    def delete(self, doc_id: str) -> bool:
        """Delete document"""
        try:
            document = self.get_by_id(doc_id)
            if not document:
                return False
            
            db.session.delete(document)
            db.session.commit()
            logger.info(f"Deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            db.session.rollback()
            return False
    
    def search_by_title(self, title_query: str) -> List[Document]:
        """Search documents by title"""
        try:
            return Document.query.filter(
                Document.title.contains(title_query)
            ).all()
        except Exception as e:
            logger.error(f"Error searching documents by title: {e}")
            return []