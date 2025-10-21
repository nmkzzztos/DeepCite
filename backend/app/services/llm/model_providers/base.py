"""
Base model provider interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.ai_models import GenerationResult, EmbeddingResult, RerankingResult, ModelInfo

class ModelProvider(ABC):
    """Abstract base class for AI model providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider with configuration"""
        self.config = config
        self._available_models = {}
    
    @abstractmethod
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate text using a language model
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model_id: ID of the model to use
            max_completion_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            GenerationResult with generated text and metadata
        """
        pass
    
    @abstractmethod
    async def embed(
        self, 
        texts: List[str], 
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """
        Generate embeddings for texts
        
        Args:
            texts: List of texts to embed
            model_id: ID of the embedding model to use
            **kwargs: Additional model-specific parameters
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        pass
    
    @abstractmethod
    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        model_id: str,
        **kwargs
    ) -> RerankingResult:
        """
        Rerank documents based on relevance to query
        
        Args:
            query: The search query
            documents: List of documents to rerank
            model_id: ID of the reranking model to use
            **kwargs: Additional model-specific parameters
            
        Returns:
            RerankingResult with relevance scores
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from this provider
        
        Returns:
            List of ModelInfo objects describing available models
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the provider is healthy and accessible
        
        Returns:
            Dict with health status information
        """
        pass
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self._available_models.get(model_id)
    
    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available from this provider"""
        return model_id in self._available_models