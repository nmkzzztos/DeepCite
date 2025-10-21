"""
Repository for paragraph data access
"""
from typing import List, Optional
from app import db
from app.models.paragraph import Paragraph
import logging

logger = logging.getLogger(__name__)


class ParagraphRepository:
    """Repository for paragraph operations"""
    
    def get_all(self) -> List[Paragraph]:
        """Get all paragraphs"""
        try:
            return Paragraph.query.all()
        except Exception as e:
            logger.error(f"Error getting all paragraphs: {e}")
            return []
    
    def get_by_id(self, para_id: str) -> Optional[Paragraph]:
        """Get paragraph by ID"""
        try:
            return Paragraph.query.filter_by(para_id=para_id).first()
        except Exception as e:
            logger.error(f"Error getting paragraph {para_id}: {e}")
            return None
    
    def get_by_document(self, doc_id: str) -> List[Paragraph]:
        """Get all paragraphs for a document"""
        try:
            return Paragraph.query.filter_by(doc_id=doc_id).order_by(
                Paragraph.page, Paragraph.para_idx
            ).all()
        except Exception as e:
            logger.error(f"Error getting paragraphs for document {doc_id}: {e}")
            return []
    
    def count_by_document(self, doc_id: str) -> int:
        """Count paragraphs for a document"""
        try:
            return Paragraph.query.filter_by(doc_id=doc_id).count()
        except Exception as e:
            logger.error(f"Error counting paragraphs for document {doc_id}: {e}")
            return 0
    
    def get_by_page(self, doc_id: str, page: int) -> List[Paragraph]:
        """Get paragraphs for a specific page"""
        try:
            return Paragraph.query.filter_by(
                doc_id=doc_id, page=page
            ).order_by(Paragraph.para_idx).all()
        except Exception as e:
            logger.error(f"Error getting paragraphs for page {page} of document {doc_id}: {e}")
            return []
    
    def create(self, **kwargs) -> Optional[Paragraph]:
        """Create a new paragraph"""
        try:
            paragraph = Paragraph(**kwargs)
            db.session.add(paragraph)
            db.session.commit()
            logger.info(f"Created paragraph {paragraph.para_id}")
            return paragraph
        except Exception as e:
            logger.error(f"Error creating paragraph: {e}")
            db.session.rollback()
            return None
    
    def delete(self, para_id: str) -> bool:
        """Delete paragraph"""
        try:
            paragraph = self.get_by_id(para_id)
            if not paragraph:
                return False
            
            db.session.delete(paragraph)
            db.session.commit()
            logger.info(f"Deleted paragraph {para_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting paragraph {para_id}: {e}")
            db.session.rollback()
            return False
    
    def search_by_text(self, text_query: str, doc_id: str = None) -> List[Paragraph]:
        """Search paragraphs by text content"""
        try:
            query = Paragraph.query.filter(
                Paragraph.text.contains(text_query)
            )
            
            if doc_id:
                query = query.filter_by(doc_id=doc_id)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error searching paragraphs by text: {e}")
            return []