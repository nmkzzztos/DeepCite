"""
Embedding model for storing vector representations metadata
Note: Actual vectors are stored in Chroma, this model tracks metadata
"""
from datetime import datetime
from app import db

class Embedding(db.Model):
    __tablename__ = 'embeddings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    para_id = db.Column(db.String(36), db.ForeignKey('paragraphs.para_id'), nullable=False)
    model = db.Column(db.Text, nullable=False)
    chroma_id = db.Column(db.Text, nullable=False)  # ID in Chroma collection
    collection_name = db.Column(db.Text, nullable=False)  # ChromaDB collection name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Helper property to access workspaces through paragraph -> document -> workspaces
    @property
    def workspaces(self):
        """Get all workspaces that contain this embedding's document"""
        if self.paragraph and self.paragraph.document:
            return self.paragraph.document.workspaces
        return []
    
    # Index for efficient model-based queries
    __table_args__ = (
        db.Index('idx_embeddings_model', 'model'),
        db.Index('idx_embeddings_chroma_id', 'chroma_id'),
        db.Index('idx_embeddings_para_model', 'para_id', 'model'),
        db.Index('idx_embeddings_collection', 'collection_name'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'para_id': self.para_id,
            'model': self.model,
            'chroma_id': self.chroma_id,
            'collection_name': self.collection_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'workspaces': [p.workspace_id for p in self.workspaces] if self.workspaces else []
        }