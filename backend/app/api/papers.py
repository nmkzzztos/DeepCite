"""
Papers API endpoints for DeepCite
"""
import logging
import re
import asyncio
from flask import Blueprint, request, jsonify
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from app.services.llm.model_provider_manager import get_model_provider_manager

logger = logging.getLogger(__name__)

papers_bp = Blueprint('papers', __name__)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=5)

def run_async(func):
    """Decorator to run async functions in Flask"""
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running, use thread pool
            future = executor.submit(asyncio.run, func(*args, **kwargs))
            return future.result()
        else:
            return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


@papers_bp.route('/search/perplexity', methods=['POST'])
@run_async
async def search_papers_with_perplexity():
    """Search for arXiv papers using Perplexity AI with arxiv.org domain filter"""
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: query'
            }), 400

        query = data['query'].strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query cannot be empty'
            }), 400

        max_results = data.get('max_results', 10)
        if max_results < 1 or max_results > 50:
            max_results = 10  # Default to 10 if invalid

        logger.info(f"Searching papers with Perplexity: {query}")

        # Get model provider manager
        provider_manager = get_model_provider_manager()
        if not provider_manager:
            raise RuntimeError("Model provider manager is not available")

        # Prepare messages for Perplexity
        system_prompt = """You are an expert researcher helping users find academic papers on arXiv.
        When searching for papers, focus on finding the most relevant and recent papers from arXiv.org.
        Always include the full arXiv paper URLs (e.g., https://arxiv.org/abs/XXXX.XXXXX) in your response.
        Format your response with clear paper recommendations, including titles, authors, and direct links to the papers.
        Be thorough but concise in your explanations."""

        user_message = f"""Please find {max_results} relevant academic papers on arXiv about: {query}

        For each paper, please provide:
        1. The full arXiv URL (e.g., https://arxiv.org/abs/XXXX.XXXXX)
        2. Paper title
        3. Authors
        4. A brief summary of what the paper is about
        5. Why it's relevant to the query

        Focus only on papers from arXiv.org and ensure all URLs are valid arXiv links."""

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]

        # Use Perplexity with arxiv.org domain filter
        result = await provider_manager.generate(
            messages=messages,
            model_id='sonar',  # Use Sonar for web search
            custom_domains=['arxiv.org'],  # Filter to only arxiv.org
            return_sources=True,
            return_related_questions=False,
            max_completion_tokens=2000
        )

        if not result:
            raise RuntimeError("Perplexity returned no result")

        response_text = ""
        if hasattr(result, 'text') and result.text:
            response_text = result.text
        elif result:
            response_text = str(result)
        else:
            logger.warning("Perplexity returned empty result")
            response_text = ""

        # Extract arXiv paper URLs from the response
        arxiv_urls = extract_arxiv_urls(response_text)
        logger.info(f"Extracted {len(arxiv_urls)} arXiv URLs from Perplexity response")

        # Extract arXiv IDs from URLs for frontend to fetch
        arxiv_ids = []
        for url in arxiv_urls[:max_results]:  # Limit to max_results
            arxiv_id_match = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)', url)
            if arxiv_id_match:
                arxiv_id = arxiv_id_match.group(1)
                if arxiv_id not in arxiv_ids:
                    arxiv_ids.append(arxiv_id)
                    logger.debug(f"Extracted arXiv ID: {arxiv_id}")

        # If we couldn't extract from URLs, try to get them directly from search results
        if not arxiv_ids and hasattr(result, 'metadata') and result.metadata:
            search_results = result.metadata.get('search_results', [])
            if search_results:
                for search_result in search_results:
                    if isinstance(search_result, dict):
                        url = search_result.get('url', '')
                        if url and 'arxiv.org' in url:
                            arxiv_id_match = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)', url)
                            if arxiv_id_match:
                                arxiv_id = arxiv_id_match.group(1)
                                if arxiv_id not in arxiv_ids:
                                    arxiv_ids.append(arxiv_id)
                                    logger.debug(f"Extracted arXiv ID from search results: {arxiv_id}")

        logger.info(f"Total arXiv IDs extracted: {len(arxiv_ids)}")

        return jsonify({
            'success': True,
            'arxiv_ids': arxiv_ids,
            'query': query,
            'total_found': len(arxiv_ids),
            'perplexity_response': response_text
        })

    except Exception as e:
        logger.error(f"Error searching papers with Perplexity: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def extract_arxiv_urls(text: str) -> List[str]:
    """Extract arXiv URLs from text"""
    if not text:
        return []

    # Pattern to match arXiv URLs
    arxiv_pattern = r'https?://arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+(?:v[0-9]+)?)'
    matches = re.findall(arxiv_pattern, text)

    urls = []
    for match in matches:
        # Convert to abs URL format
        url = f"https://arxiv.org/abs/{match}"
        if url not in urls:
            urls.append(url)

    # Also look for patterns like "arXiv:XXXX.XXXXX"
    arxiv_id_pattern = r'arXiv:([0-9]+\.[0-9]+(?:v[0-9]+)?)'
    id_matches = re.findall(arxiv_id_pattern, text)

    for match in id_matches:
        url = f"https://arxiv.org/abs/{match}"
        if url not in urls:
            urls.append(url)

    return urls




@papers_bp.route('/health', methods=['GET'])
def papers_health():
    """Check papers service health"""
    try:
        return jsonify({
            'success': True,
            'status': 'healthy',
            'service': 'papers'
        })
    except Exception as e:
        logger.error(f"Papers health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500
