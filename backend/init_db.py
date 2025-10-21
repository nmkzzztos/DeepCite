#!/usr/bin/env python3
"""
Database initialization script for DeepCite
"""
import os
import logging
from sqlalchemy import text
from app import create_app, db

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with direct table creation"""
    app = create_app()
    
    with app.app_context():
        # Import models to ensure they're registered
        from app.models import Document, Paragraph, Embedding, Workspace, workspace_documents
        
        print("Creating database tables...")
        
        # Drop existing tables if they exist (for clean setup)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Run additional migrations if needed
        try:
            # Check if embeddings table has new structure
            result = db.session.execute(text("PRAGMA table_info(embeddings)"))
            columns = {row[1]: row for row in result.fetchall()}
            
            if 'collection_name' not in columns or 'id' not in columns:
                logger.info("Running embeddings table migration...")
                
                # Backup existing data
                backup_data = []
                try:
                    result = db.session.execute(text("SELECT * FROM embeddings"))
                    backup_data = result.fetchall()
                    logger.info(f"Backed up {len(backup_data)} existing embedding records")
                except Exception as e:
                    logger.info(f"No existing embeddings data to backup: {e}")
                
                # Drop and recreate embeddings table
                db.session.execute(text("DROP TABLE IF EXISTS embeddings"))
                
                # Create new embeddings table structure
                create_embeddings_sql = """
                CREATE TABLE embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    para_id VARCHAR(36) NOT NULL,
                    model TEXT NOT NULL,
                    chroma_id TEXT NOT NULL,
                    collection_name TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(para_id) REFERENCES paragraphs (para_id)
                )
                """
                db.session.execute(text(create_embeddings_sql))
                
                # Create indexes
                indexes = [
                    "CREATE INDEX idx_embeddings_model ON embeddings (model)",
                    "CREATE INDEX idx_embeddings_chroma_id ON embeddings (chroma_id)",
                    "CREATE INDEX idx_embeddings_para_model ON embeddings (para_id, model)",
                    "CREATE INDEX idx_embeddings_collection ON embeddings (collection_name)"
                ]
                
                for index_sql in indexes:
                    db.session.execute(text(index_sql))
                
                # Restore data with default collection names
                if backup_data:
                    logger.info("Restoring existing data with default collection names...")
                    for row in backup_data:
                        # Handle both old and new structure
                        if len(row) == 4:  # Old structure: para_id, model, chroma_id, created_at
                            para_id, model, chroma_id, created_at = row
                        else:  # In case there are other variations
                            continue
                        
                        collection_name = f"embeddings_{model.replace('-', '_').replace('/', '_')}"
                        
                        insert_sql = """
                        INSERT INTO embeddings (para_id, model, chroma_id, collection_name, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """
                        
                        db.session.execute(text(insert_sql), (
                            para_id, model, chroma_id, collection_name, created_at
                        ))
                    
                    logger.info(f"Restored {len(backup_data)} embedding records")
                
                db.session.commit()
                logger.info("Embeddings table migration completed")
                
        except Exception as e:
            logger.warning(f"Migration check failed (may be expected): {e}")
        
        # Verify tables were created
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        
        expected_tables = ['documents', 'paragraphs', 'embeddings', 'workspaces', 'workspace_documents']
        missing_tables = [table for table in expected_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            print(f"ERROR: Missing tables: {missing_tables}")
        else:
            logger.info("All required tables created successfully")
            print("Database initialization complete!")
            print(f"Created tables: {', '.join(sorted(tables))}")

if __name__ == '__main__':
    init_database()