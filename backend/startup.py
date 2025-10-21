#!/usr/bin/env python3
"""
Startup script for DeepCite - initializes database and vector collections
"""
import os
import sys
from app import create_app, db

def initialize_system():
    """Initialize the DeepCite system"""
    print("🚀 Initializing DeepCite system...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize database
            print("📊 Initializing database...")
            db.create_all()
            print("✅ Database initialized successfully")
            
            # Initialize vector collections
            print("🔍 Initializing vector collections...")
            collections = [
                'documents_openai',  # OpenAI embeddings
                'documents_local',   # Local embeddings
            ]
            
            print("🎉 DeepCite system initialized successfully!")
            print("\n📋 Next steps:")
            print("1. Start the backend: python app.py")
            print("2. Start the frontend: cd frontend && npm run dev")
            print("3. Or use Docker Compose: docker-compose up")
            
        except Exception as e:
            print(f"❌ Error initializing system: {e}")
            sys.exit(1)

if __name__ == '__main__':
    initialize_system()