"""
RAG (Retrieval-Augmented Generation) service for DeepCite
"""
import logging
from typing import List, Dict, Any, Optional
from flask import current_app

from app.services.embedding_service import EmbeddingService
from app.models.paragraph import Paragraph
from app.models.document import Document
from app.models.workspace import Workspace
from app.logging_config import timing_logger
from app import db

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    @timing_logger('app.services.rag')
    def search_documents(
        self,
        query: str,
        workspace_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        max_results: int = 20,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document passages using RAG
        
        Args:
            query: Search query text
            workspace_ids: Optional list of workspace IDs to limit search to
            document_ids: Optional list of document IDs to limit search to
            model_id: Embedding model to use for search
            max_results: Maximum number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of relevant passages with metadata
        """
        try:
            # Determine which documents to search
            target_doc_ids = self._get_target_document_ids(workspace_ids, document_ids)
            
            if not target_doc_ids:
                logger.warning("RAG_SEARCH_NO_DOCUMENTS: No processed documents found for search criteria")
                return []
            
            logger.info(f"RAG_EMBEDDING_SEARCH_START: Searching {len(target_doc_ids)} documents for query (length: {len(query)} chars)")

            # Search for similar paragraphs
            similar_paragraphs = self.embedding_service.search_similar_paragraphs(
                query_text=query,
                model_id=model_id,
                n_results=max_results * 2,  # Get more results to filter by score
                doc_ids=target_doc_ids
            )

            logger.info(f"RAG_EMBEDDING_SEARCH_RESULTS: Embedding service returned {len(similar_paragraphs)} similar paragraphs")
            if similar_paragraphs:
                logger.debug(f"RAG_EMBEDDING_TOP_RESULTS: Top scores: {[p.get('score', 0) for p in similar_paragraphs[:5]]}")
            
            # Filter by minimum score and format results
            results = []
            for paragraph in similar_paragraphs:
                if paragraph['score'] >= min_score:
                    # Get additional paragraph metadata from database
                    para_obj = db.session.query(Paragraph).filter_by(
                        para_id=paragraph['para_id']
                    ).first()

                    if para_obj:
                        # Get document info
                        doc_obj = db.session.query(Document).filter_by(
                            doc_id=para_obj.doc_id
                        ).first()

                        result = {
                            'paragraph_id': paragraph['para_id'],
                            'text': paragraph['text'],
                            'score': paragraph['score'],
                            'page': paragraph['metadata'].get('page'),
                            'section_path': paragraph['metadata'].get('section_path', ''),
                            'document': {
                                'id': para_obj.doc_id,
                                'title': doc_obj.title if doc_obj else 'Unknown',
                                'authors': doc_obj.authors if doc_obj else [],
                                'year': doc_obj.year if doc_obj else None
                            }
                        }
                        results.append(result)
                    else:
                        logger.warning(f"RAG_SEARCH_PARAGRAPH_NOT_FOUND: Paragraph {paragraph['para_id']} not found in database")

                if len(results) >= max_results:
                    break

            logger.info(f"RAG_SEARCH_SUCCESS: Found {len(results)} relevant passages (filtered from {len(similar_paragraphs)})")
            return results
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            return []
    
    @timing_logger('app.services.rag')
    def _get_target_document_ids(
        self,
        workspace_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get list of document IDs to search based on workspace and document filters
        
        Args:
            workspace_ids: Optional list of workspace IDs
            document_ids: Optional list of document IDs
            
        Returns:
            List of document IDs to search
        """
        try:
            from app.models.workspace import workspace_documents
            from app.models.paragraph import Paragraph
            
            logger.info(f"RAG_TARGET_DOCS_START: Searching for documents with workspace_ids: {workspace_ids}, document_ids: {document_ids}")

            # First, let's check what documents exist in the specified workspaces
            if workspace_ids:
                workspace_docs = db.session.query(Document.doc_id).join(workspace_documents).filter(
                    workspace_documents.c.workspace_id.in_(workspace_ids)
                ).all()
                logger.info(f"RAG_WORKSPACE_DOCS: Found {len(workspace_docs)} documents in workspaces {workspace_ids}: {[d[0] for d in workspace_docs]}")

            # Check what documents have paragraphs
            docs_with_paragraphs = db.session.query(Document.doc_id).join(Paragraph).distinct().all()
            logger.info(f"RAG_PROCESSED_DOCS: Found {len(docs_with_paragraphs)} documents with paragraphs: {[d[0] for d in docs_with_paragraphs]}")
            
            # Start with a simple query to get all documents
            if workspace_ids and document_ids:
                # If both workspace and document filters are specified, use document filter
                # (since documents are already filtered by workspace in the frontend)
                doc_ids = document_ids
                logger.info(f"Using provided document IDs: {doc_ids}")
            elif document_ids:
                # Only document filter
                doc_ids = document_ids
                logger.info(f"Using provided document IDs: {doc_ids}")
            elif workspace_ids:
                # Only workspace filter - get all documents in these workspaces
                query = db.session.query(Document.doc_id).join(workspace_documents).filter(
                    workspace_documents.c.workspace_id.in_(workspace_ids)
                )
                doc_ids = [row[0] for row in query.all()]
                logger.info(f"Found documents in workspaces: {doc_ids}")
            else:
                # No filters - this shouldn't happen in normal usage
                doc_ids = []
                logger.info("No workspace or document filters provided")
            
            # Filter out documents that don't have paragraphs (not processed yet)
            if doc_ids:
                processed_docs = db.session.query(Document.doc_id).filter(
                    Document.doc_id.in_(doc_ids)
                ).join(Paragraph).distinct().all()
                doc_ids = [row[0] for row in processed_docs]
                logger.info(f"RAG_FILTERED_DOCS: After filtering for processed documents: {len(doc_ids)} docs - {doc_ids}")
            else:
                logger.info("RAG_NO_DOCS_FILTER: No document filtering applied")
            logger.info(f"RAG_TARGET_DOCS_SUCCESS: Found {len(doc_ids)} documents matching criteria: {doc_ids}")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Error getting target document IDs: {e}")
            return []
    
    @timing_logger('app.services.rag')
    def generate_context_from_search(
        self,
        search_results: List[Dict[str, Any]],
        max_context_length: int = 4000
    ) -> str:
        """
        Generate context string from search results for use in chat
        
        Args:
            search_results: List of search results from search_documents
            max_context_length: Maximum length of context to generate
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(search_results, 1):
            # Format the passage with metadata
            doc_info = result['document']
            citation = f"{doc_info['title']}"
            if doc_info['authors']:
                citation += f" by {', '.join(doc_info['authors'])}"
            if doc_info['year']:
                citation += f" ({doc_info['year']})"
            
            passage = f"[Source {i}: {citation}]\n"
            if result['page']:
                passage += f"Page: {result['page']}\n"
            passage += f"Content: {result['text']}\n"
            passage += f"Relevance Score: {result['score']:.3f}\n\n"
            
            # Check if adding this passage would exceed the limit
            if current_length + len(passage) > max_context_length:
                break
            
            context_parts.append(passage)
            current_length += len(passage)
        
        if context_parts:
            context = "Based on the following relevant passages from your documents:\n\n"
            context += "".join(context_parts)
            context += "Please answer the question using the information from these sources. "
            context += "Cite the sources using the [Source X] format when referencing specific information."
        else:
            context = ""
        
        return context
    
    def search_and_generate_context(
        self,
        query: str,
        workspace_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        max_results: int = 20,
        max_context_length: int = 4000
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Search for relevant documents and generate context for chat
        
        Args:
            query: Search query
            workspace_ids: Optional workspace filter
            document_ids: Optional document filter
            model_id: Embedding model to use
            max_results: Maximum search results
            max_context_length: Maximum context length
            
        Returns:
            Tuple of (context_string, search_results)
        """
        search_results = self.search_documents(
            query=query,
            workspace_ids=workspace_ids,
            document_ids=document_ids,
            model_id=model_id,
            max_results=max_results
        )
        
        context = self.generate_context_from_search(
            search_results=search_results,
            max_context_length=max_context_length
        )
        
        return context, search_results