"""
OpenAI model provider implementation
"""
import time
import logging
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI

from .base import ModelProvider
from app.models.ai_models import (
    GenerationResult, EmbeddingResult, RerankingResult, 
    ModelInfo, ModelType
)

logger = logging.getLogger(__name__)

class OpenAIProvider(ModelProvider):
    """OpenAI API provider for language models and embeddings"""
    
    # Available OpenAI models with their specifications
    AVAILABLE_MODELS = {
        'gpt-5': ModelInfo(
            id='gpt-5',
            name='GPT 5',
            provider='openai',
            type=ModelType.GENERATION,
            max_completion_tokens=1000000,
            description='GPT-5 with advanced reasoning capabilities',
            supports_top_p=False
        ),
        'gpt-5-mini': ModelInfo(
            id='gpt-5-mini',
            name='GPT-5 mini',
            provider='openai',
            type=ModelType.GENERATION,
            max_completion_tokens=1000000,
            description='GPT 5 Mini - Advanced reasoning model',
            supports_top_p=False
        ),
        'gpt-5-nano': ModelInfo(
            id='gpt-5-nano',
            name='GPT 5 Nano',
            provider='openai',
            type=ModelType.GENERATION,
            max_completion_tokens=1000000,
            description='GPT 5 Nano - Advanced reasoning model',
            supports_top_p=False
        ),
        'text-embedding-3-small': ModelInfo(
            id='text-embedding-3-small',
            name='Embedding v3 Small',
            provider='openai',
            type=ModelType.EMBEDDING,
            embedding_dimension=1536,
            description='Smaller, faster embedding model'
        ),
        'text-embedding-3-large': ModelInfo(
            id='text-embedding-3-large',
            name='Embedding v3 Large',
            provider='openai',
            type=ModelType.EMBEDDING,
            embedding_dimension=3072,
            description='Most capable embedding model'
        ),
        'text-embedding-ada-002': ModelInfo(
            id='text-embedding-ada-002',
            name='Ada v2',
            provider='openai',
            type=ModelType.EMBEDDING,
            embedding_dimension=1536,
            description='Legacy embedding model (deprecated)'
        )
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI provider"""
        super().__init__(config)
        
        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.get('base_url'),
        )
        
        # Store available models
        self._available_models = self.AVAILABLE_MODELS.copy()
        
        logger.info(f"Initialized OpenAI provider with {len(self._available_models)} models")
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        model_id: str,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using OpenAI models"""
        
        if not self.is_model_available(model_id):
            raise ValueError(f"Model {model_id} not available from OpenAI provider")
        
        model_info = self.get_model_info(model_id)
        if model_info.type != ModelType.GENERATION:
            raise ValueError(f"Model {model_id} is not a generation model")
        
        try:
            # Prepare request parameters - use chat completions for standard models
            request_params = {
                'model': model_id,
                'messages': messages,
            }
            
            if max_completion_tokens:
                request_params['max_tokens'] = max_completion_tokens
            
            # Filter out parameters that the current OpenAI client doesn't support
            filtered_kwargs = {}
            unsupported_params = ['reasoning_effort']  # Add other unsupported params here
            
            for key, value in kwargs.items():
                if key not in unsupported_params:
                    filtered_kwargs[key] = value
                else:
                    logger.warning(f"Parameter '{key}' not supported by OpenAI client, skipping")
            
            # Add filtered additional parameters
            request_params.update(filtered_kwargs)
            
            logger.debug(f"Making OpenAI generation request with model {model_id}")
            
            # Check if this is a reasoning model (GPT-5 series) that needs the responses API
            if model_id.startswith('gpt-5'):
                # Use the responses API for GPT-5 models
                response = self.client.responses.create(
                    model=model_id,
                    input=messages,
                    reasoning={'effort': 'high'},
                    **filtered_kwargs
                )

                # Handle new response format
                if hasattr(response, 'output') and response.output:
                    # Find the assistant message in the output
                    assistant_message = None
                    for item in response.output:
                        if hasattr(item, 'role') and item.role == 'assistant':
                            assistant_message = item
                            break
                    
                    if assistant_message and hasattr(assistant_message, 'content'):
                        # Extract text from content
                        text_content = ""
                        for content_item in assistant_message.content:
                            if hasattr(content_item, 'text'):
                                text_content += content_item.text
                        
                        return GenerationResult(
                            text=text_content,
                            model=model_id,
                            usage={
                                'prompt_tokens': response.usage.input_tokens,
                                'completion_tokens': response.usage.output_tokens,
                                'total_tokens': response.usage.total_tokens
                            },
                            metadata={
                                'finish_reason': assistant_message.status if hasattr(assistant_message, 'status') else 'completed',
                                'response_id': response.id,
                                'created': response.created_at
                            }
                        )
                    else:
                        raise RuntimeError("No assistant message found in response output")
                else:
                    raise RuntimeError("Invalid response format from OpenAI API")
            else:
                # Use standard chat completions for other models
                response = self.client.chat.completions.create(**request_params)
                
                return GenerationResult(
                    text=response.choices[0].message.content,
                    model=model_id,
                    usage={
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    },
                    metadata={
                        'finish_reason': response.choices[0].finish_reason,
                        'response_id': response.id,
                        'created': response.created
                    }
                )
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise RuntimeError(f"OpenAI generation failed: {str(e)}")
    
    async def embed(
        self, 
        texts: List[str], 
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """Generate embeddings using OpenAI models"""
        
        if not self.is_model_available(model_id):
            raise ValueError(f"Model {model_id} not available from OpenAI provider")
        
        model_info = self.get_model_info(model_id)
        if model_info.type != ModelType.EMBEDDING:
            raise ValueError(f"Model {model_id} is not an embedding model")
        
        try:
            logger.debug(f"Making OpenAI embedding request with model {model_id} for {len(texts)} texts")
            
            response = self.client.embeddings.create(
                model=model_id,
                input=texts,
                **kwargs
            )
            
            embeddings = [data.embedding for data in response.data]
            
            return EmbeddingResult(
                embeddings=embeddings,
                model=model_id,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                metadata={
                    'response_id': response.id if hasattr(response, 'id') else None,
                    'embedding_dimension': len(embeddings[0]) if embeddings else 0
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            raise RuntimeError(f"OpenAI embedding failed: {str(e)}")
    
    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        model_id: str,
        **kwargs
    ) -> RerankingResult:
        """
        OpenAI doesn't have dedicated reranking models, so we'll use embeddings
        to compute similarity scores as a fallback
        """
        
        # For now, we'll use embedding similarity as a reranking method
        # This is a fallback since OpenAI doesn't have dedicated reranking models
        
        try:
            # Get embeddings for query and documents
            all_texts = [query] + documents
            embed_result = await self.embed(all_texts, model_id)
            
            query_embedding = embed_result.embeddings[0]
            doc_embeddings = embed_result.embeddings[1:]
            
            # Compute cosine similarity scores
            scores = []
            for doc_embedding in doc_embeddings:
                # Cosine similarity
                dot_product = sum(a * b for a, b in zip(query_embedding, doc_embedding))
                norm_query = sum(a * a for a in query_embedding) ** 0.5
                norm_doc = sum(a * a for a in doc_embedding) ** 0.5
                
                if norm_query == 0 or norm_doc == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_query * norm_doc)
                
                scores.append(similarity)
            
            return RerankingResult(
                scores=scores,
                model=model_id,
                usage=embed_result.usage,
                metadata={
                    'method': 'embedding_similarity',
                    'note': 'Using embedding similarity as OpenAI does not have dedicated reranking models'
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI reranking error: {str(e)}")
            raise RuntimeError(f"OpenAI reranking failed: {str(e)}")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models"""
        return list(self._available_models.values())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health"""
        try:
            # Try a simple API call to check connectivity
            models = self.client.models.list()
            
            return {
                'status': 'healthy',
                'provider': 'openai',
                'available_models': len(self._available_models),
                'api_accessible': True,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'provider': 'openai',
                'error': str(e),
                'api_accessible': False,
                'timestamp': time.time()
            }