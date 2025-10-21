"""
workspace model for organizing documents into collections
"""
from datetime import datetime
from app import db
import uuid
import json

class Workspace(db.Model):
    __tablename__ = 'workspaces'
    
    workspace_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to documents through workspace_documents association table
    documents = db.relationship('Document', secondary='workspace_documents', back_populates='workspaces')
    
    @property
    def embeddings(self):
        """Get all embeddings for all documents in this workspace"""
        from app.models.embedding import Embedding
        embeddings = []
        for document in self.documents:
            for paragraph in document.paragraphs:
                embeddings.extend(paragraph.embeddings)
        return embeddings
    
    @property
    def paragraphs(self):
        """Get all paragraphs for all documents in this workspace"""
        paragraphs = []
        for document in self.documents:
            paragraphs.extend(document.paragraphs)
        return paragraphs
    
    def to_dict(self):
        return {
            'workspace_id': self.workspace_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'document_count': len(self.documents),
            'paragraph_count': len(self.paragraphs),
            'embedding_count': len(self.embeddings)
        }


# Association table for many-to-many relationship between workspaces and documents
workspace_documents = db.Table('workspace_documents',
    db.Column('workspace_id', db.String(36), db.ForeignKey('workspaces.workspace_id'), primary_key=True),
    db.Column('doc_id', db.String(36), db.ForeignKey('documents.doc_id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)