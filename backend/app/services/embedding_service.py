"""
Embedding service for generating and managing document embeddings
"""
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from app.models.embedding import Embedding
from app.models.paragraph import Paragraph
from app.services.llm.model_provider_manager import ModelProviderManager
from app.models.ai_models import get_embedding_models, ModelInfo, EmbeddingResult
from app import db
from flask import current_app

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings with different models"""
    
    def __init__(self):
        self.model_manager = None
        self.chroma_client = None
        self._initialized = False
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client"""
        try:
            chroma_path = current_app.config.get('CHROMA_PERSIST_DIRECTORY', './chroma_db')
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            logger.info(f"Initialized ChromaDB client at {chroma_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _initialize_model_manager(self):
        """Initialize model provider manager"""
        try:
            # Use the already initialized model provider manager from the app
            self.model_manager = current_app.model_provider_manager
            if self.model_manager is None:
                raise RuntimeError("Model provider manager not initialized in app")
            logger.info("Using app model provider manager")
        except Exception as e:
            logger.error(f"Failed to initialize model provider manager: {e}")
            raise
    
    def get_available_embedding_models(self) -> List[ModelInfo]:
        """Get list of available embedding models"""
        self._ensure_initialized()
        return get_embedding_models()
    
    def get_default_embedding_model(self) -> str:
        """Get the default embedding model ID"""
        return current_app.config.get('DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-small')
    
    def _ensure_initialized(self):
        """Ensure service is fully initialized"""
        if not self._initialized:
            self._initialize_chroma()
            self._initialize_model_manager()
            self._initialized = True
    
    def _generate_embeddings_sync(self, texts: List[str], model_id: str) -> EmbeddingResult:
        """Synchronous wrapper for generating embeddings"""
        import asyncio
        import concurrent.futures
        
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, use a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_embed_in_new_loop, texts, model_id)
                return future.result()
        except RuntimeError:
            # No event loop running, we can create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.model_manager.embed(texts, model_id)
                )
            finally:
                loop.close()
    
    def _run_embed_in_new_loop(self, texts: List[str], model_id: str) -> EmbeddingResult:
        """Run embedding in a new event loop (for thread pool execution)"""
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.model_manager.embed(texts, model_id)
            )
        finally:
            loop.close()
    
    def generate_embeddings_for_paragraphs(
        self,
        paragraphs: List[Paragraph],
        model_id: Optional[str] = None,
        batch_size: int = 100
    ) -> bool:
        """
        Generate embeddings for a list of paragraphs using specified model

        Args:
            paragraphs: List of paragraph objects
            model_id: Embedding model to use (defaults to configured default)
            batch_size: Number of paragraphs to process in each batch

        Returns:
            True if successful, False otherwise
        """
        if not paragraphs:
            logger.warning("No paragraphs provided for embedding generation")
            return True

        if not model_id:
            model_id = self.get_default_embedding_model()

        logger.info(f"Generating embeddings for {len(paragraphs)} paragraphs using model {model_id}")

        try:
            # Validate model is available
            available_models = {m.id for m in self.get_available_embedding_models()}
            if model_id not in available_models:
                logger.error(f"Embedding model {model_id} not available. Available models: {available_models}")
                return False

            # Filter out paragraphs that already have embeddings for this model
            para_ids = [p.para_id for p in paragraphs]
            existing_embeddings = db.session.query(Embedding.para_id).filter(
                Embedding.para_id.in_(para_ids),
                Embedding.model == model_id
            ).all()

            existing_para_ids = {emb.para_id for emb in existing_embeddings}

            if existing_para_ids:
                logger.info(f"Found {len(existing_para_ids)} paragraphs that already have embeddings for model {model_id}")
                # Filter out paragraphs that already have embeddings
                paragraphs_to_process = [p for p in paragraphs if p.para_id not in existing_para_ids]
                if not paragraphs_to_process:
                    logger.info("All paragraphs already have embeddings, skipping generation")
                    return True
                paragraphs = paragraphs_to_process
                logger.info(f"Processing {len(paragraphs)} new paragraphs")

            # Get or create ChromaDB collection for this model
            collection_name = f"embeddings_{model_id.replace('-', '_').replace('/', '_')}"
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"embedding_model": model_id}
            )

            # Process paragraphs in batches
            for i in range(0, len(paragraphs), batch_size):
                batch = paragraphs[i:i + batch_size]

                try:
                    self._process_paragraph_batch(batch, model_id, collection)
                except Exception as e:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                    # Continue with next batch rather than failing completely
                    continue

            # Commit all embedding records to database
            db.session.commit()
            logger.info(f"Successfully generated embeddings for {len(paragraphs)} paragraphs using {model_id}")
            return True

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            db.session.rollback()
            return False
    
    def _process_paragraph_batch(
        self, 
        batch: List[Paragraph], 
        model_id: str, 
        collection
    ):
        """Process a batch of paragraphs for embedding generation"""
        texts = [p.text for p in batch]
        ids = [p.para_id for p in batch]
        
        # Generate embeddings using the model provider
        self._ensure_initialized()
        embedding_result = self._generate_embeddings_sync(texts, model_id)
        
        if not embedding_result.success:
            raise Exception(f"Failed to generate embeddings: {embedding_result.error}")
        
        # Prepare metadata for ChromaDB
        metadatas = []
        for paragraph in batch:
            metadata = {
                'doc_id': paragraph.doc_id,
                'page': paragraph.page,
                'para_idx': paragraph.para_idx,
                'section_path': paragraph.section_path or '',
                'type': paragraph.type or 'paragraph',
                'tokens': paragraph.tokens or 0
            }
            metadatas.append(metadata)
        
        # Add to ChromaDB
        collection.add(
            documents=texts,
            embeddings=embedding_result.embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Create embedding records in database for tracking
        for paragraph in batch:
            embedding = Embedding(
                para_id=paragraph.para_id,
                model=model_id,
                chroma_id=paragraph.para_id,
                collection_name=collection.name
            )
            db.session.add(embedding)
    
    def delete_embeddings_for_document(self, doc_id: str) -> bool:
        """
        Delete all embeddings for a document from all collections
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_initialized()
            
            # Get all embeddings for this document
            embeddings = db.session.query(Embedding).join(Paragraph).filter(
                Paragraph.doc_id == doc_id
            ).all()
            
            if not embeddings:
                logger.info(f"No embeddings found for document {doc_id}")
                return True
            
            # Group by collection name
            collections_to_clean = {}
            for embedding in embeddings:
                collection_name = embedding.collection_name
                if collection_name not in collections_to_clean:
                    collections_to_clean[collection_name] = []
                collections_to_clean[collection_name].append(embedding.chroma_id)
            
            # Delete from ChromaDB collections
            for collection_name, chroma_ids in collections_to_clean.items():
                try:
                    collection = self.chroma_client.get_collection(collection_name)
                    collection.delete(ids=chroma_ids)
                    logger.info(f"Deleted {len(chroma_ids)} embeddings from collection {collection_name}")
                except Exception as e:
                    logger.error(f"Error deleting from ChromaDB collection {collection_name}: {e}")
            
            # Delete embedding records from database
            for embedding in embeddings:
                db.session.delete(embedding)
            
            db.session.commit()
            logger.info(f"Successfully deleted all embeddings for document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embeddings for document {doc_id}: {e}")
            db.session.rollback()
            return False
    
    def search_similar_paragraphs(
        self, 
        query_text: str, 
        model_id: Optional[str] = None,
        n_results: int = 10,
        doc_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar paragraphs using embedding similarity
        
        Args:
            query_text: Text to search for
            model_id: Embedding model to use for search
            n_results: Number of results to return
            doc_ids: Optional list of document IDs to limit search to
            
        Returns:
            List of similar paragraphs with scores
        """
        if not model_id:
            model_id = self.get_default_embedding_model()
        
        try:
            self._ensure_initialized()
            
            # Get collection for this model
            collection_name = f"embeddings_{model_id.replace('-', '_').replace('/', '_')}"
            try:
                collection = self.chroma_client.get_collection(collection_name)
            except Exception as e:
                logger.error(f"Collection {collection_name} not found: {e}")
                return []
            
            # Generate embedding for query
            self._ensure_initialized()
            embedding_result = self._generate_embeddings_sync([query_text], model_id)
            
            if not embedding_result.success:
                logger.error(f"Failed to generate query embedding: {embedding_result.error}")
                return []
            
            # Prepare where clause for document filtering
            where_clause = None
            if doc_ids:
                where_clause = {"doc_id": {"$in": doc_ids}}
            
            # Search in ChromaDB
            results = collection.query(
                query_embeddings=embedding_result.embeddings,
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            similar_paragraphs = []
            if results['ids'] and results['ids'][0]:
                for i, para_id in enumerate(results['ids'][0]):
                    similar_paragraphs.append({
                        'para_id': para_id,
                        'text': results['documents'][0][i],
                        'score': 2 - results['distances'][0][i],  # Convert distance to similarity
                        'metadata': results['metadatas'][0][i]
                    })
            
            return similar_paragraphs
            
        except Exception as e:
            logger.error(f"Error searching similar paragraphs: {e}")
            return []
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embeddings in the system"""
        try:
            self._ensure_initialized()
            # Get counts by model
            model_counts = db.session.query(
                Embedding.model,
                db.func.count(Embedding.id).label('count')
            ).group_by(Embedding.model).all()
            
            # Get total count
            total_embeddings = db.session.query(Embedding).count()
            
            # Get collection info from ChromaDB
            collections = self.chroma_client.list_collections()
            collection_info = []
            
            for collection in collections:
                try:
                    coll = self.chroma_client.get_collection(collection.name)
                    count = coll.count()
                    metadata = collection.metadata or {}
                    collection_info.append({
                        'name': collection.name,
                        'count': count,
                        'model': metadata.get('embedding_model', 'unknown')
                    })
                except Exception as e:
                    logger.error(f"Error getting info for collection {collection.name}: {e}")
            
            return {
                'total_embeddings': total_embeddings,
                'models': [{'model': model, 'count': count} for model, count in model_counts],
                'collections': collection_info,
                'available_models': [model.to_dict() for model in self.get_available_embedding_models()]
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            return {
                'total_embeddings': 0,
                'models': [],
                'collections': [],
                'available_models': []
            }