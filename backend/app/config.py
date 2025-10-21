"""
Configuration management for DeepCite
"""
import os
from typing import Dict, Any

class Config:
    """Base configuration class"""
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///deepcite.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # File Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Chroma Vector Database
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_db')
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'localhost')
    CHROMA_PORT = int(os.getenv('CHROMA_PORT', 8000))
    CHROMA_TELEMETRY_ENABLED = os.getenv('CHROMA_TELEMETRY_ENABLED', 'false').lower() == 'true'
    
    # AI Model Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    # Local Model Configuration
    OLLAMA_ENDPOINT = os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434')
    LLAMACPP_ENDPOINT = os.getenv('LLAMACPP_ENDPOINT', 'http://localhost:8080')
    ENABLE_LOCAL_MODELS = os.getenv('ENABLE_LOCAL_MODELS', 'false').lower() == 'true'
    
    # Default Models
    DEFAULT_EMBEDDING_MODEL = os.getenv('DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-small')
    DEFAULT_GENERATION_MODEL = os.getenv('DEFAULT_GENERATION_MODEL', 'gpt-5-nano')
    DEFAULT_RERANKING_MODEL = os.getenv('DEFAULT_RERANKING_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    @property
    def MODEL_PROVIDERS_CONFIG(self):
        """Configuration for model providers"""
        config = {
            'providers': {},
            'defaults': {
                'embedding': self.DEFAULT_EMBEDDING_MODEL,
                'generation': self.DEFAULT_GENERATION_MODEL,
                'reranking': self.DEFAULT_RERANKING_MODEL
            }
        }
        
        # Add OpenAI provider if API key is available
        if self.OPENAI_API_KEY:
            config['providers']['openai'] = {
                'type': 'openai',
                'api_key': self.OPENAI_API_KEY,
                'timeout': 30,
                'max_retries': 3
            }
            
        # Add Perplexity provider if API key is available
        if self.PERPLEXITY_API_KEY:
            config['providers']['perplexity'] = {
                'type': 'perplexity',
                'api_key': self.PERPLEXITY_API_KEY,
                'timeout': 30,
                'max_retries': 3
            }
            
        if self.OPENROUTER_API_KEY:
            config['providers']['openrouter'] = {
                'type': 'openrouter',
                'api_key': self.OPENROUTER_API_KEY,
                'timeout': 30,
                'max_retries': 3
            }
        
        # Add other providers as they become available
        if self.ANTHROPIC_API_KEY:
            config['providers']['anthropic'] = {
                'type': 'anthropic',
                'api_key': self.ANTHROPIC_API_KEY,
                'timeout': 30,
                'max_retries': 3
            }
        
        if self.GOOGLE_API_KEY:
            config['providers']['google'] = {
                'type': 'google',
                'api_key': self.GOOGLE_API_KEY,
                'timeout': 30,
                'max_retries': 3
            }
        
        # Add local model providers if enabled
        if self.ENABLE_LOCAL_MODELS:
            config['providers']['ollama'] = {
                'type': 'ollama',
                'endpoint': self.OLLAMA_ENDPOINT,
                'timeout': 60,
                'max_retries': 2
            }
            
            config['providers']['llamacpp'] = {
                'type': 'llamacpp',
                'endpoint': self.LLAMACPP_ENDPOINT,
                'timeout': 60,
                'max_retries': 2
            }
        
        return config
    
    # Processing Configuration
    EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', 1536))
    MAX_TOKENS_PER_CHUNK = int(os.getenv('MAX_TOKENS_PER_CHUNK', 512))
    RETRIEVAL_TOP_K = int(os.getenv('RETRIEVAL_TOP_K', 10))
    RERANK_TOP_K = int(os.getenv('RERANK_TOP_K', 5))
    
    # PDF Parsing Configuration
    GROBID_URL = os.getenv('GROBID_URL', 'http://localhost:8070')
    DEFAULT_PARSING_STRATEGY = os.getenv('DEFAULT_PARSING_STRATEGY', 'auto')  # auto, grobid, toc, standard
    ENABLE_GROBID = os.getenv('ENABLE_GROBID', 'true').lower() == 'true'
    ENABLE_TOC_PARSING = os.getenv('ENABLE_TOC_PARSING', 'true').lower() == 'true'
    
    # TOC Parsing Options
    TOC_MIN_LEVEL = int(os.getenv('TOC_MIN_LEVEL', 1))
    TOC_MAX_LEVEL = int(os.getenv('TOC_MAX_LEVEL', 6))
    TOC_INCLUDE_MISSING_SECTIONS = os.getenv('TOC_INCLUDE_MISSING_SECTIONS', 'true').lower() == 'true'
    TOC_INCLUDE_CHILDREN_TEXT = os.getenv('TOC_INCLUDE_CHILDREN_TEXT', 'true').lower() == 'true'
    TOC_OWN_ONLY = os.getenv('TOC_OWN_ONLY', 'false').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CHROMA_PERSIST_DIRECTORY = ':memory:'  # In-memory for tests

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}