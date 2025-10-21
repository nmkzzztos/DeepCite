"""
Perplexity model provider implementation
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

class PerplexityProvider(ModelProvider):
    """Perplexity API provider for language models with web search capabilities"""

    # Available Perplexity models with their specifications
    AVAILABLE_MODELS = {
        'sonar': ModelInfo(
            id='sonar',
            name='Sonar',
            provider='perplexity',
            type=ModelType.GENERATION,
            max_completion_tokens=100000,
            description='Perplexity Sonar - Real-time web search with AI answers'
        ),
        'sonar-pro': ModelInfo(
            id='sonar-pro',
            name='Sonar Pro',
            provider='perplexity',
            type=ModelType.GENERATION,
            max_completion_tokens=200000,
            description='Perplexity Sonar Pro - Enhanced web search with citations'
        ),
        'sonar-reasoning': ModelInfo(
            id='sonar-reasoning',
            name='Sonar Reasoning',
            provider='perplexity',
            type=ModelType.GENERATION,
            max_completion_tokens=100000,
            description='Perplexity Sonar Reasoning - Advanced reasoning capabilities'
        ),
        'sonar-reasoning-pro': ModelInfo(
            id='sonar-reasoning-pro',
            name='Sonar Reasoning Pro',
            provider='perplexity',
            type=ModelType.GENERATION,
            max_completion_tokens=200000,
            description='Perplexity Sonar Reasoning Pro - Professional reasoning model'
        ),
        'sonar-deep-research': ModelInfo(
            id='sonar-deep-research',
            name='Sonar Deep Research',
            provider='perplexity',
            type=ModelType.GENERATION,
            max_completion_tokens=500000,
            description='Perplexity Sonar Deep Research - Deep analysis and research'
        )
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize Perplexity provider"""
        super().__init__(config)

        api_key = config.get('api_key')
        if not api_key:
            raise ValueError("Perplexity API key is required")

        self.api_key = api_key

        # Store available models
        self._available_models = self.AVAILABLE_MODELS.copy()

        logger.info(f"Initialized Perplexity provider with {len(self._available_models)} models")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model_id: str,
        max_completion_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text using Perplexity models with optional custom domains"""

        if not self.is_model_available(model_id):
            raise ValueError(f"Model {model_id} not available from Perplexity provider")

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

            # Handle Perplexity-specific parameters
            # Extract custom domains from kwargs
            custom_domains = kwargs.pop('custom_domains', None)
            if custom_domains:
                if isinstance(custom_domains, list):
                    payload['search_domain_filter'] = custom_domains
                else:
                    payload['search_domain_filter'] = [custom_domains]
                logger.info(f"Using custom domains for search: {payload['search_domain_filter']}")

            # Extract other Perplexity-specific parameters
            search_recency_filter = kwargs.pop('search_recency_filter', None)
            if search_recency_filter:
                payload['search_recency_filter'] = search_recency_filter

            return_sources = kwargs.pop('return_sources', True)
            payload['return_sources'] = return_sources

            return_related_questions = kwargs.pop('return_related_questions', False)
            payload['return_related_questions'] = return_related_questions

            # Add supported OpenAI-compatible parameters
            supported_params = {
                'temperature', 'top_p', 'top_k', 'presence_penalty',
                'frequency_penalty', 'stream', 'seed'
            }

            for key, value in kwargs.items():
                if key in supported_params:
                    payload[key] = value

            logger.debug(f"Making Perplexity API request with model {model_id}")

            # Make direct HTTP request to Perplexity API
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code != 200:
                    error_msg = f"Perplexity API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                response_data = response.json()

                # Extract the response content
                content = response_data['choices'][0]['message']['content']

                # Extract citations and search results if available
                citations = []
                search_results = []
                formatted_citations = []

                if 'citations' in response_data:
                    citations = response_data['citations']

                if 'search_results' in response_data:
                    search_results = response_data['search_results']

                    # Create formatted citations for replacement
                    for i, result in enumerate(search_results, 1):
                        formatted_citations.append({
                            'index': i,
                            'title': result.get('title', 'Unknown Title'),
                            'url': result.get('url', ''),
                            'date': result.get('date', ''),
                            'snippet': result.get('snippet', ''),
                            'last_updated': result.get('last_updated', '')
                        })

                # Replace [1][2] etc. with actual citations in the content
                if formatted_citations:
                    import re
                    for citation in formatted_citations:
                        # Replace patterns like [1], [2], etc. with clickable links
                        pattern = r'\[(' + str(citation['index']) + r')\]'
                        title = citation['title'][:50] + "..." if len(citation['title']) > 50 else citation['title']
                        replacement = f"[\\[{citation['index']}\\]]({citation['url']} \"{title}\")"
                        content = re.sub(pattern, replacement, content)

                # Prepare metadata
                metadata = {
                    'finish_reason': response_data['choices'][0]['finish_reason'],
                    'response_id': response_data['id'],
                    'created': response_data['created'],
                    'model': response_data['model'],
                    'citations': citations,
                    'search_results': search_results,
                    'formatted_citations': formatted_citations
                }

                # Add Perplexity-specific metadata from usage
                if 'usage' in response_data:
                    usage = response_data['usage']
                    if 'citations' in usage:
                        metadata['citations_count'] = len(usage['citations']) if usage['citations'] else 0
                    if 'search_queries' in usage:
                        metadata['search_queries'] = usage['search_queries']

                return GenerationResult(
                    text=content,
                    model=model_id,
                    usage={
                        'prompt_tokens': response_data['usage'].get('prompt_tokens', 0),
                        'completion_tokens': response_data['usage'].get('completion_tokens', 0),
                        'total_tokens': response_data['usage'].get('total_tokens', 0)
                    },
                    metadata=metadata
                )

        except Exception as e:
            logger.error(f"Perplexity generation error: {str(e)}")
            raise RuntimeError(f"Perplexity generation failed: {str(e)}")

    async def embed(
        self,
        texts: List[str],
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """Generate embeddings using Perplexity models (if supported)"""

        # Perplexity doesn't currently support embeddings
        raise NotImplementedError("Perplexity provider does not support embedding operations")

    async def rerank(
        self,
        query: str,
        documents: List[str],
        model_id: str,
        **kwargs
    ) -> RerankingResult:
        """
        Perplexity doesn't have dedicated reranking models.
        We'll use a simple approach for now.
        """

        # For now, return equal scores since Perplexity doesn't have reranking
        scores = [1.0] * len(documents)

        return RerankingResult(
            scores=scores,
            model=model_id,
            metadata={
                'method': 'equal_weighting',
                'note': 'Perplexity does not have dedicated reranking models'
            }
        )

    async def list_models(self) -> List[ModelInfo]:
        """List available Perplexity models"""
        return list(self._available_models.values())

    async def health_check(self) -> Dict[str, Any]:
        """Check Perplexity API health"""
        try:
            # Try a simple API call to check connectivity
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 1
                    }
                )

            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'provider': 'perplexity',
                    'available_models': len(self._available_models),
                    'api_accessible': True,
                    'timestamp': time.time()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'provider': 'perplexity',
                    'error': f"API returned status {response.status_code}",
                    'api_accessible': False,
                    'timestamp': time.time()
                }

        except Exception as e:
            logger.error(f"Perplexity health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'provider': 'perplexity',
                'error': str(e),
                'api_accessible': False,
                'timestamp': time.time()
            }
