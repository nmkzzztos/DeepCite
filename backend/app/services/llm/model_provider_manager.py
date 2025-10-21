"""
Model provider manager for handling multiple AI providers
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from app.models.ai_models import (
    GenerationResult, EmbeddingResult, RerankingResult, 
    ModelInfo, ModelConfig, ProviderType
)
from app.services.llm.model_providers import ModelProvider, OpenAIProvider, PerplexityProvider, OpenRouterProvider

logger = logging.getLogger(__name__)

class ModelProviderManager:
    """Manages multiple AI model providers and routes requests"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider manager with configuration"""
        self.config = config
        self.providers: Dict[str, ModelProvider] = {}
        self._model_to_provider: Dict[str, str] = {}
        
        # Initialize providers based on configuration
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers"""
        providers_config = self.config.get('providers', {})
        
        for provider_name, provider_config in providers_config.items():
            try:
                provider = self._create_provider(provider_name, provider_config)
                if provider:
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized provider: {provider_name}")
                    
                    # Build model-to-provider mapping (will be done lazily when needed)
                    
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {str(e)}")
    
    def _create_provider(self, name: str, config: Dict[str, Any]) -> Optional[ModelProvider]:
        """Create a provider instance based on configuration"""
        provider_type = config.get('type', '').lower()

        if provider_type == 'openai' or name.lower() == 'openai':
            return OpenAIProvider(config)
        elif provider_type == 'perplexity' or name.lower() == 'perplexity':
            return PerplexityProvider(config)
        elif provider_type == 'openrouter' or name.lower() == 'openrouter':
            return OpenRouterProvider(config)
        else:
            logger.warning(f"Unknown provider type: {provider_type}")
            return None
    
    async def _update_model_mapping(self, provider_name: str, provider: ModelProvider):
        """Update the model-to-provider mapping"""
        try:
            models = await provider.list_models()
            for model in models:
                self._model_to_provider[model.id] = provider_name
        except Exception as e:
            logger.error(f"Failed to update model mapping for {provider_name}: {str(e)}")
    
    def get_provider_for_model(self, model_id: str) -> Optional[ModelProvider]:
        """Get the provider that supports a specific model"""
        provider_name = self._model_to_provider.get(model_id)
        if provider_name:
            return self.providers.get(provider_name)
        
        # Fallback: check all providers
        for provider_name, provider in self.providers.items():
            if provider.is_model_available(model_id):
                # Cache the mapping for future use
                self._model_to_provider[model_id] = provider_name
                return provider
        
        return None
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using the appropriate provider"""
        provider = self.get_provider_for_model(model_id)
        if not provider:
            raise ValueError(f"No provider available for model: {model_id}")
        
        return await provider.generate(messages, model_id, max_completion_tokens, **kwargs)
    
    async def embed(
        self, 
        texts: List[str], 
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """Generate embeddings using the appropriate provider"""
        provider = self.get_provider_for_model(model_id)
        if not provider:
            raise ValueError(f"No provider available for model: {model_id}")
        
        return await provider.embed(texts, model_id, **kwargs)
    
    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        model_id: str,
        **kwargs
    ) -> RerankingResult:
        """Rerank documents using the appropriate provider"""
        provider = self.get_provider_for_model(model_id)
        if not provider:
            raise ValueError(f"No provider available for model: {model_id}")
        
        return await provider.rerank(query, documents, model_id, **kwargs)
    
    async def list_all_models(self) -> List[ModelInfo]:
        """List all available models from all providers"""
        all_models = []
        
        for provider_name, provider in self.providers.items():
            try:
                models = await provider.list_models()
                all_models.extend(models)
            except Exception as e:
                logger.error(f"Failed to list models from {provider_name}: {str(e)}")
        
        return all_models
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        health_status = {}
        
        for provider_name, provider in self.providers.items():
            try:
                status = await provider.health_check()
                health_status[provider_name] = status
            except Exception as e:
                health_status[provider_name] = {
                    'status': 'error',
                    'error': str(e),
                    'provider': provider_name
                }
        
        return health_status
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """Get a specific provider by name"""
        return self.providers.get(name)

# Global instance - will be initialized by the application
model_provider_manager: Optional[ModelProviderManager] = None

def get_model_provider_manager() -> ModelProviderManager:
    """Get the global model provider manager instance"""
    if model_provider_manager is None:
        raise RuntimeError("Model provider manager not initialized")
    return model_provider_manager

def initialize_model_provider_manager(config: Dict[str, Any]) -> ModelProviderManager:
    """Initialize the global model provider manager"""
    global model_provider_manager
    model_provider_manager = ModelProviderManager(config)
    return model_provider_manager