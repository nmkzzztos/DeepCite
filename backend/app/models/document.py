"""
Document model for storing PDF metadata
"""
from datetime import datetime
from app import db
import uuid
import json

class Document(db.Model):
    __tablename__ = 'documents'
    
    doc_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text, default='[]')  # JSON string for SQLite compatibility
    year = db.Column(db.Integer)
    source = db.Column(db.Text)
    sha256 = db.Column(db.Text, unique=True, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    lang = db.Column(db.Text, default='en')
    file_path = db.Column(db.Text)  # Path to the original PDF file
    additional_metadata = db.Column(db.Text, default='{}')  # JSON string for additional parsing metadata
    
    @property
    def authors_list(self):
        """Get authors as a list"""
        try:
            return json.loads(self.authors) if self.authors else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    @authors_list.setter
    def authors_list(self, value):
        """Set authors from a list"""
        self.authors = json.dumps(value) if value else '[]'
    
    @property
    def additional_metadata_dict(self):
        """Get additional metadata as a dictionary"""
        try:
            return json.loads(self.additional_metadata) if self.additional_metadata else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @additional_metadata_dict.setter
    def additional_metadata_dict(self, value):
        """Set additional metadata from a dictionary"""
        self.additional_metadata = json.dumps(value) if value else '{}'
    
    # Relationship to paragraphs
    paragraphs = db.relationship('Paragraph', backref='document', lazy=True, cascade='all, delete-orphan')
    
    # Relationship to workspaces through workspace_documents association table
    workspaces = db.relationship('Workspace', secondary='workspace_documents', back_populates='documents')
    
    def to_dict(self):
        result = {
            'doc_id': self.doc_id,
            'title': self.title,
            'authors': self.authors_list,
            'year': self.year,
            'source': self.source,
            'sha256': self.sha256,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'lang': self.lang
        }
        
        # Add additional metadata if available
        additional_meta = self.additional_metadata_dict
        if additional_meta:
            result['parsing_metadata'] = additional_meta
        
        return result