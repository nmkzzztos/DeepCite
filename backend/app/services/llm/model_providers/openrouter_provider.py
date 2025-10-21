"""
OpenRouter model provider implementation
"""
import time
import logging
from typing import List, Dict, Any, Optional
import httpx

from .base import ModelProvider
from app.models.ai_models import (
    GenerationResult, EmbeddingResult, RerankingResult,
    ModelInfo, ModelType
)

logger = logging.getLogger(__name__)

class OpenRouterProvider(ModelProvider):
    """OpenRouter API provider for unified access to multiple AI models"""

    # Predefined models with their specifications (these will be supplemented by dynamic fetching)
    PREDEFINED_MODELS = {
        # OpenAI GPT-5 series
        'openai/gpt-5': ModelInfo(
            id='openai/gpt-5',
            name='GPT-5',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=400000,
            description='GPT-5 is OpenAI\'s most advanced model, offering major improvements in reasoning, code quality, and user experience. It is optimized for complex tasks that require step-by-step reasoning, instruction following, and accuracy in high-stakes use cases.',
        ),
        'openai/gpt-5-mini': ModelInfo(
            id='openai/gpt-5-mini',
            name='GPT-5 Mini',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=400000,
            description='GPT-5 Mini is a compact version of GPT-5, designed to handle lighter-weight reasoning tasks. It provides the same instruction-following and safety-tuning benefits as GPT-5, but with reduced latency and cost.',
        ),
        'openai/gpt-5-nano': ModelInfo(
            id='openai/gpt-5-nano',
            name='GPT-5 Nano',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=400000,
            description='GPT-5-Nano is the smallest and fastest variant in the GPT-5 system, optimized for developer tools, rapid interactions, and ultra-low latency environments.',
        ),
        # Anthropic models
        'anthropic/claude-opus-4.1': ModelInfo(
            id='anthropic/claude-opus-4.1',
            name='Claude Opus 4.1',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=200000,
            description='Claude Opus 4.1 is an updated version of Anthropic\'s flagship model, offering improved performance in coding, reasoning, and agentic tasks.',
        ),
        'anthropic/claude-sonnet-4': ModelInfo(
            id='anthropic/claude-sonnet-4',
            name='Claude Sonnet 4',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=1000000,
            description='Claude Sonnet 4 significantly enhances the capabilities of its predecessor, Sonnet 3.7, excelling in both coding and reasoning tasks with improved precision and controllability.',
        ),
        # Google Gemini models
        'google/gemini-2.5-flash-lite': ModelInfo(
            id='google/gemini-2.5-flash-lite',
            name='Gemini 2.5 Flash Lite',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=1050000,
            description='Gemini 2.5 Flash-Lite is a lightweight reasoning model in the Gemini 2.5 family, optimized for ultra-low latency and cost efficiency.',
        ),
        'google/gemini-2.5-flash': ModelInfo(
            id='google/gemini-2.5-flash',
            name='Gemini 2.5 Flash',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=1050000,
            description='Gemini 2.5 Flash is Google\'s state-of-the-art workhorse model, specifically designed for advanced reasoning, coding, mathematics, and scientific tasks.',
        ),
        'google/gemini-2.5-pro': ModelInfo(
            id='google/gemini-2.5-pro',
            name='Gemini 2.5 Pro',
            provider='openrouter',
            type=ModelType.GENERATION,
            max_completion_tokens=1050000,
            description='Gemini 2.5 Pro is Google\'s state-of-the-art AI model designed for advanced reasoning, coding, mathematics, and scientific tasks.',
        ),
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenRouter provider"""
        super().__init__(config)

        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("OpenRouter API key is required")

        self.api_key = api_key
        self.base_url = config.get('base_url', 'https://openrouter.ai/api/v1')

        # Start with predefined models, will be supplemented by dynamic fetching
        self._available_models = self.PREDEFINED_MODELS.copy()
        self._models_fetched = False

        logger.info("Initialized OpenRouter provider")

    async def _fetch_available_models(self):
        """Fetch available models from OpenRouter API"""
        if self._models_fetched:
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to fetch OpenRouter models: {response.status_code}")
                    return

                models_data = response.json()
                models = {}

                for model_data in models_data.get('data', []):
                    model_id = model_data.get('id', '')
                    if not model_id:
                        continue

                    # Determine model type based on capabilities
                    model_type = ModelType.GENERATION  # Default
                    if 'embedding' in model_id.lower() or model_data.get('description', '').lower().find('embedding') != -1:
                        model_type = ModelType.EMBEDDING

                    # Extract context length
                    context_length = model_data.get('context_length', 4096)

                    model_info = ModelInfo(
                        id=model_id,
                        name=model_data.get('name', model_id),
                        provider='openrouter',
                        type=model_type,
                        max_completion_tokens=context_length,
                        description=model_data.get('description', ''),
                        embedding_dimension=model_data.get('embedding_length') if model_type == ModelType.EMBEDDING else None
                    )

                    models[model_id] = model_info

                # Merge fetched models with predefined ones (don't overwrite predefined)
                for model_id, model_info in models.items():
                    if model_id not in self._available_models:
                        self._available_models[model_id] = model_info

                self._models_fetched = True
                logger.info(f"Fetched {len(models)} additional models from OpenRouter (total: {len(self._available_models)})")

        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {str(e)}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model_id: str,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using OpenRouter models"""

        await self._fetch_available_models()

        if not self.is_model_available(model_id):
            raise ValueError(f"Model {model_id} not available from OpenRouter provider")

        model_info = self.get_model_info(model_id)
        if model_info.type != ModelType.GENERATION:
            raise ValueError(f"Model {model_id} is not a generation model")

        try:
            # Prepare request payload
            payload = {
                'model': model_id,
                'messages': messages,
            }

            if max_completion_tokens:
                payload['max_tokens'] = max_completion_tokens

            # Add supported OpenAI-compatible parameters
            supported_params = {
                'temperature', 'top_p', 'top_k', 'presence_penalty',
                'frequency_penalty', 'stream', 'seed', 'stop', 'logit_bias'
            }

            for key, value in kwargs.items():
                if key in supported_params:
                    payload[key] = value

            # Add optional headers for app attribution
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Add optional attribution headers
            site_url = kwargs.get('site_url')
            site_name = kwargs.get('site_name')
            if site_url:
                headers["HTTP-Referer"] = site_url
            if site_name:
                headers["X-Title"] = site_name

            logger.debug(f"Making OpenRouter generation request with model {model_id}")

            # Make direct HTTP request to OpenRouter API
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                response_data = response.json()

                return GenerationResult(
                    text=response_data['choices'][0]['message']['content'],
                    model=model_id,
                    usage={
                        'prompt_tokens': response_data['usage'].get('prompt_tokens', 0),
                        'completion_tokens': response_data['usage'].get('completion_tokens', 0),
                        'total_tokens': response_data['usage'].get('total_tokens', 0)
                    },
                    metadata={
                        'finish_reason': response_data['choices'][0]['finish_reason'],
                        'response_id': response_data['id'],
                        'created': response_data['created'],
                        'model': response_data.get('model', model_id),
                    }
                )

        except Exception as e:
            logger.error(f"OpenRouter generation error: {str(e)}")
            raise RuntimeError(f"OpenRouter generation failed: {str(e)}")

    async def embed(
        self,
        texts: List[str],
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """Generate embeddings using OpenRouter models"""

        await self._fetch_available_models()

        if not self.is_model_available(model_id):
            raise ValueError(f"Model {model_id} not available from OpenRouter provider")

        model_info = self.get_model_info(model_id)
        if model_info.type != ModelType.EMBEDDING:
            raise ValueError(f"Model {model_id} is not an embedding model")

        try:
            logger.debug(f"Making OpenRouter embedding request with model {model_id} for {len(texts)} texts")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        'model': model_id,
                        'input': texts,
                        **kwargs
                    }
                )

                if response.status_code != 200:
                    error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                response_data = response.json()

                embeddings = [data['embedding'] for data in response_data['data']]

                return EmbeddingResult(
                    embeddings=embeddings,
                    model=model_id,
                    usage={
                        'prompt_tokens': response_data['usage'].get('prompt_tokens', 0),
                        'total_tokens': response_data['usage'].get('total_tokens', 0)
                    },
                    metadata={
                        'response_id': response_data.get('id'),
                        'embedding_dimension': len(embeddings[0]) if embeddings else 0
                    }
                )

        except Exception as e:
            logger.error(f"OpenRouter embedding error: {str(e)}")
            raise RuntimeError(f"OpenRouter embedding failed: {str(e)}")

    async def rerank(
        self,
        query: str,
        documents: List[str],
        model_id: str,
        **kwargs
    ) -> RerankingResult:
        """
        OpenRouter doesn't have dedicated reranking models, so we'll use embeddings
        to compute similarity scores as a fallback
        """

        await self._fetch_available_models()

        # Look for an embedding model to use for reranking
        embedding_model = None
        for model_info in self._available_models.values():
            if model_info.type == ModelType.EMBEDDING:
                embedding_model = model_info.id
                break

        if not embedding_model:
            raise ValueError("No embedding model available for reranking")

        try:
            # Get embeddings for query and documents
            all_texts = [query] + documents
            embed_result = await self.embed(all_texts, embedding_model)

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
                    'embedding_model': embedding_model,
                    'note': 'Using embedding similarity as OpenRouter does not have dedicated reranking models'
                }
            )

        except Exception as e:
            logger.error(f"OpenRouter reranking error: {str(e)}")
            raise RuntimeError(f"OpenRouter reranking failed: {str(e)}")

    async def list_models(self) -> List[ModelInfo]:
        """List available OpenRouter models"""
        await self._fetch_available_models()
        return list(self._available_models.values())

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenRouter API health"""
        try:
            # Try a simple API call to check connectivity
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code == 200:
                models_data = response.json()
                return {
                    'status': 'healthy',
                    'provider': 'openrouter',
                    'available_models': len(models_data.get('data', [])),
                    'api_accessible': True,
                    'timestamp': time.time()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'openrouter',
                    'error': f"API returned status {response.status_code}",
                    'api_accessible': False,
                    'timestamp': time.time()
                }

        except Exception as e:
            logger.error(f"OpenRouter health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'provider': 'openrouter',
                'error': str(e),
                'api_accessible': False,
                'timestamp': time.time()
            }
