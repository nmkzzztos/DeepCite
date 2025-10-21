"""
Paragraph model for storing document segments with coordinates
"""
from datetime import datetime
from app import db
import uuid
import json

class Paragraph(db.Model):
    __tablename__ = 'paragraphs'
    
    para_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id = db.Column(db.String(36), db.ForeignKey('documents.doc_id'), nullable=False)
    page = db.Column(db.Integer, nullable=False)
    para_idx = db.Column(db.Integer, nullable=False)
    section_path = db.Column(db.Text)
    text = db.Column(db.Text, nullable=False)
    bbox = db.Column(db.Text)  # JSON string for SQLite compatibility
    char_span = db.Column(db.Text)  # JSON string for SQLite compatibility
    type = db.Column(db.Text, default='paragraph')  # paragraph, figure_caption, table
    tokens = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def bbox_dict(self):
        """Get bbox as a dictionary"""
        try:
            return json.loads(self.bbox) if self.bbox else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    @bbox_dict.setter
    def bbox_dict(self, value):
        """Set bbox from a dictionary"""
        self.bbox = json.dumps(value) if value else None
    
    @property
    def char_span_dict(self):
        """Get char_span as a dictionary"""
        try:
            return json.loads(self.char_span) if self.char_span else None
        except (json.JSONDecodeError, TypeError):
            return None
    
    @char_span_dict.setter
    def char_span_dict(self, value):
        """Set char_span from a dictionary"""
        self.char_span = json.dumps(value) if value else None
    
    # Relationship to embeddings
    embeddings = db.relationship('Embedding', backref='paragraph', lazy=True, cascade='all, delete-orphan')
    
    @property
    def workspaces(self):
        """Get all workspaces that contain this paragraph's document"""
        if self.document:
            return self.document.workspaces
        return []
    
    # Indexes
    __table_args__ = (
        db.Index('idx_paragraphs_doc_page', 'doc_id', 'page'),
        db.Index('idx_paragraphs_section', 'section_path'),
    )
    
    def to_dict(self):
        return {
            'para_id': self.para_id,
            'doc_id': self.doc_id,
            'page': self.page,
            'para_idx': self.para_idx,
            'section_path': self.section_path,
            'text': self.text,
            'bbox': self.bbox_dict,
            'char_span': self.char_span_dict,
            'type': self.type,
            'tokens': self.tokens,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'workspaces': [p.workspace_id for p in self.workspaces] if self.workspaces else [],
            'embedding_count': len(self.embeddings)
        }