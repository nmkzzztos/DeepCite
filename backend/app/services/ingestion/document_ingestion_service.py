"""
Document ingestion service that orchestrates the processing pipeline.
"""
import os
import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import uuid

from ..parsing.pdf_content_extractor import PDFParser, ParsedDocument
from ..parsing.paragraph_segmenter import TextSegmenter, SegmentedParagraph
from ..parsing.document_parser import GlobalPDFParser, ParsingStrategy, GlobalParseResult
from ...models import Document, Paragraph
from ...repositories import DocumentRepository, ParagraphRepository
from app import db

logger = logging.getLogger(__name__)


class IngestionStatus(Enum):
    """Status of document ingestion process."""
    PENDING = "pending"
    PARSING_PDF = "parsing_pdf"
    EXTRACTING_STRUCTURE = "extracting_structure"
    SEGMENTING_TEXT = "segmenting_text"
    SAVING_TO_DATABASE = "saving_to_database"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionProgress:
    """Progress information for document ingestion."""
    status: IngestionStatus
    progress_percent: float
    current_step: str
    total_steps: int
    completed_steps: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status.value,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class IngestionResult:
    """Result of document ingestion process."""
    success: bool
    doc_id: Optional[str] = None
    document: Optional[Document] = None
    paragraphs_count: int = 0
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    progress: Optional[IngestionProgress] = None


class DocumentIngestionService:
    """
    Service that orchestrates the complete document processing pipeline.
    
    This service handles:
    1. PDF parsing with PyMuPDF
    2. TOC-based structure extraction
    3. Text segmentation into paragraphs
    4. Database storage
    5. Vector embedding generation (optional)
    6. Progress tracking and error handling
    """
    
    def __init__(
        self,
        enable_embeddings: bool = False,
        embedding_model_id: Optional[str] = None,
        parsing_strategy: ParsingStrategy = ParsingStrategy.AUTO,
        toc_options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the document ingestion service.
        
        Args:
            enable_embeddings: Whether to generate embeddings during ingestion
            embedding_model_id: ID of the embedding model to use (defaults to system default)
            parsing_strategy: Default parsing strategy to use
            toc_options: Options for TOC parsing
        """
        # Enhanced PDF parser that supports multiple strategies
        self.enhanced_parser = GlobalPDFParser()
        
        # Legacy parsers for compatibility
        self.pdf_parser = PDFParser()
        self.text_segmenter = TextSegmenter()
        
        self.enable_embeddings = enable_embeddings
        self.embedding_model_id = embedding_model_id
        self.parsing_strategy = parsing_strategy
        self.toc_options = toc_options or {}
        
        # Repositories
        self.document_repo = DocumentRepository()
        self.paragraph_repo = ParagraphRepository()
        
        # Embedding service
        if enable_embeddings:
            try:
                from app.services.embedding_service import EmbeddingService
                self.embedding_service = EmbeddingService()
            except Exception as e:
                logger.warning(f"Failed to initialize embedding service: {e}")
                self.embedding_service = None
        else:
            self.embedding_service = None
        
        # Progress tracking
        self._progress_callbacks: Dict[str, Callable[[IngestionProgress], None]] = {}
        
        # Processing steps configuration
        self.total_steps = 4 if enable_embeddings else 3  # Enhanced parser reduces steps
    
    def register_progress_callback(self, job_id: str, callback: Callable[[IngestionProgress], None]):
        """Register a callback function for progress updates."""
        self._progress_callbacks[job_id] = callback
    
    def unregister_progress_callback(self, job_id: str):
        """Unregister a progress callback."""
        if job_id in self._progress_callbacks:
            del self._progress_callbacks[job_id]
    
    def _update_progress(
        self, 
        job_id: str, 
        status: IngestionStatus, 
        step: str, 
        completed_steps: int,
        error_message: Optional[str] = None
    ):
        """Update progress and notify callbacks."""
        progress_percent = (completed_steps / self.total_steps) * 100
        
        progress = IngestionProgress(
            status=status,
            progress_percent=progress_percent,
            current_step=step,
            total_steps=self.total_steps,
            completed_steps=completed_steps,
            error_message=error_message,
            started_at=getattr(self, f'_start_time_{job_id}', None),
            completed_at=datetime.utcnow() if status in [IngestionStatus.COMPLETED, IngestionStatus.FAILED] else None
        )
        
        # Call registered callback if exists
        if job_id in self._progress_callbacks:
            try:
                self._progress_callbacks[job_id](progress)
            except Exception as e:
                logger.error(f"Error in progress callback for job {job_id}: {e}")
        
        return progress
    
    def ingest_document_from_path(
        self, 
        pdf_path: str, 
        job_id: Optional[str] = None,
        metadata_override: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest a document from file path.
        
        Args:
            pdf_path: Path to PDF file
            job_id: Optional job ID for progress tracking
            metadata_override: Optional metadata to override extracted metadata
            
        Returns:
            IngestionResult with processing outcome
        """
        if not job_id:
            job_id = str(uuid.uuid4())
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            return self.ingest_document_from_bytes(pdf_bytes, job_id, metadata_override)
        except Exception as e:
            logger.error(f"Error reading PDF file {pdf_path}: {e}")
            progress = self._update_progress(
                job_id, IngestionStatus.FAILED, "Reading PDF file", 0, str(e)
            )
            return IngestionResult(
                success=False,
                error_message=f"Error reading PDF file: {e}",
                progress=progress
            )
    
    def ingest_document_from_bytes(
        self, 
        pdf_bytes: bytes, 
        job_id: Optional[str] = None,
        metadata_override: Optional[Dict[str, Any]] = None,
        embedding_model_id: Optional[str] = None
    ) -> IngestionResult:
        """
        Ingest a document from PDF bytes.
        
        Args:
            pdf_bytes: PDF file content as bytes
            job_id: Optional job ID for progress tracking
            metadata_override: Optional metadata to override extracted metadata
            embedding_model_id: Optional embedding model ID to use for this document
            
        Returns:
            IngestionResult with processing outcome
        """
        if not job_id:
            job_id = str(uuid.uuid4())
        
        start_time = datetime.utcnow()
        setattr(self, f'_start_time_{job_id}', start_time)
        
        try:
            # Step 1: Parse PDF with Enhanced Parser
            progress = self._update_progress(
                job_id, IngestionStatus.PARSING_PDF, f"Parsing PDF with {self.parsing_strategy.value} strategy", 0
            )
            
            # Merge toc_options with metadata_override for TOC parsing
            parse_options = dict(self.toc_options)
            if metadata_override and 'parsing_options' in metadata_override:
                parse_options.update(metadata_override['parsing_options'])
            
            enhanced_result = self.enhanced_parser.parse_document_bytes(
                pdf_bytes, strategy=self.parsing_strategy, **parse_options
            )
            
            if not enhanced_result or not enhanced_result.document:
                error_msg = "Failed to parse PDF document"
                progress = self._update_progress(
                    job_id, IngestionStatus.FAILED, "PDF parsing failed", 0, error_msg
                )
                return IngestionResult(
                    success=False,
                    error_message=error_msg,
                    progress=progress
                )
            
            parsed_doc = enhanced_result.document
            segmented_paragraphs = enhanced_result.paragraphs
            
            logger.info(f"Parsed PDF with {enhanced_result.strategy_used.value}: {parsed_doc.page_count} pages, {len(segmented_paragraphs)} paragraphs")
            if enhanced_result.warnings:
                for warning in enhanced_result.warnings:
                    logger.warning(f"Parsing warning: {warning}")
            
            # Check if document already exists
            existing_doc = self.document_repo.get_by_sha256(parsed_doc.file_hash)
            if existing_doc:
                logger.info(f"Document with hash {parsed_doc.file_hash} already exists")
                progress = self._update_progress(
                    job_id, IngestionStatus.COMPLETED, "Document already exists", self.total_steps
                )
                return IngestionResult(
                    success=True,
                    doc_id=str(existing_doc.doc_id),
                    document=existing_doc,
                    paragraphs_count=self.paragraph_repo.count_by_document(str(existing_doc.doc_id)),
                    progress=progress
                )
            
            if not segmented_paragraphs:
                error_msg = "No paragraphs were extracted from the document"
                progress = self._update_progress(
                    job_id, IngestionStatus.FAILED, "Text segmentation failed", 1, error_msg
                )
                return IngestionResult(
                    success=False,
                    error_message=error_msg,
                    progress=progress
                )
            
            logger.info(f"Segmented into {len(segmented_paragraphs)} paragraphs")
            
            # Step 2: Save to database
            progress = self._update_progress(
                job_id, IngestionStatus.SAVING_TO_DATABASE, "Saving to database", 1
            )
            
            doc_id = str(uuid.uuid4())
            document, paragraphs = self._save_to_database_enhanced(
                enhanced_result, segmented_paragraphs, doc_id, metadata_override
            )
            
            if not document:
                error_msg = "Failed to save document to database"
                progress = self._update_progress(
                    job_id, IngestionStatus.FAILED, "Database save failed", 1, error_msg
                )
                return IngestionResult(
                    success=False,
                    error_message=error_msg,
                    progress=progress
                )
            
            logger.info(f"Saved document {doc_id} with {len(paragraphs)} paragraphs to database")
            
            # Step 3: Generate embeddings (optional)
            if self.enable_embeddings and self.embedding_service:
                progress = self._update_progress(
                    job_id, IngestionStatus.GENERATING_EMBEDDINGS, "Generating embeddings", 2
                )
                
                try:
                    # Use provided embedding model or fall back to instance/default
                    model_to_use = embedding_model_id or self.embedding_model_id
                    success = self.embedding_service.generate_embeddings_for_paragraphs(
                        paragraphs, model_id=model_to_use
                    )
                    if success:
                        logger.info(f"Generated embeddings for {len(paragraphs)} paragraphs using model {model_to_use or 'default'}")
                    else:
                        logger.error("Failed to generate embeddings")
                except Exception as e:
                    logger.error(f"Error generating embeddings: {e}")
                    # Don't fail the entire process for embedding errors
            
            # Step 4: Complete
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            progress = self._update_progress(
                job_id, IngestionStatus.COMPLETED, "Document ingestion completed", self.total_steps
            )
            
            return IngestionResult(
                success=True,
                doc_id=doc_id,
                document=document,
                paragraphs_count=len(paragraphs),
                processing_time_seconds=processing_time,
                progress=progress
            )
            
        except Exception as e:
            logger.error(f"Error during document ingestion: {e}")
            logger.error(traceback.format_exc())
            
            progress = self._update_progress(
                job_id, IngestionStatus.FAILED, "Ingestion failed", 0, str(e)
            )
            
            return IngestionResult(
                success=False,
                error_message=str(e),
                progress=progress
            )
        finally:
            # Clean up progress callback
            self.unregister_progress_callback(job_id)
    

    
    def _save_to_database_enhanced(
        self,
        enhanced_result: GlobalParseResult,
        segmented_paragraphs: List[SegmentedParagraph],
        doc_id: str,
        metadata_override: Optional[Dict[str, Any]] = None
    ) -> tuple[Optional[Document], List[Paragraph]]:
        """
        Save enhanced parsing result to database.
        
        Args:
            enhanced_result: Result from enhanced PDF parser
            segmented_paragraphs: Segmented paragraphs
            doc_id: Document ID
            metadata_override: Optional metadata overrides
            
        Returns:
            Tuple of (Document, List[Paragraph]) or (None, []) if failed
        """
        try:
            parsed_doc = enhanced_result.document
            
            # Prepare document metadata
            title = parsed_doc.metadata.title
            authors = parsed_doc.metadata.authors
            
            # Metadata is extracted from PDF parser only (no GROBID)
            
            # Apply metadata overrides
            if metadata_override:
                title = metadata_override.get('title', title)
                authors = metadata_override.get('authors', authors)
            
            # Fallback title extraction from content if needed
            if not title:
                title = self.pdf_parser.extract_document_title_from_content(parsed_doc.text_blocks)
            
            if not title:
                title = f"Document {doc_id[:8]}"
            
            # Create document record with parsing strategy info
            document = Document(
                doc_id=doc_id,
                title=title,
                year=metadata_override.get('year') if metadata_override else None,
                source=metadata_override.get('source') if metadata_override else None,
                sha256=parsed_doc.file_hash,
                lang=metadata_override.get('lang', 'en') if metadata_override else 'en'
            )
            
            # Set authors using the property setter to handle JSON conversion
            document.authors_list = authors or []
            
            # Add parsing metadata and file info
            additional_metadata = {
                'parsing_strategy': enhanced_result.strategy_used.value,
                'parsing_warnings': enhanced_result.warnings or [],
                'toc_sections_found': len(enhanced_result.toc_result.sections) if enhanced_result.toc_result else 0,
                'missing_sections_found': enhanced_result.toc_result.missing_sections_found if enhanced_result.toc_result else 0,
                'page_count': parsed_doc.page_count
            }
            
            # Add file metadata if provided
            if metadata_override:
                if 'filename' in metadata_override:
                    additional_metadata['filename'] = metadata_override['filename']
                if 'file_size' in metadata_override:
                    additional_metadata['file_size'] = metadata_override['file_size']
            
            document.additional_metadata_dict = additional_metadata
            
            # Save document
            db.session.add(document)
            db.session.flush()  # Get the ID
            
            # Create paragraph records
            paragraphs = []
            for seg_para in segmented_paragraphs:
                paragraph = Paragraph(
                    para_id=seg_para.stable_id,
                    doc_id=doc_id,
                    page=seg_para.page,
                    para_idx=seg_para.para_idx,
                    section_path=seg_para.section_path,
                    text=seg_para.text,
                    type=seg_para.paragraph_type,
                    tokens=seg_para.tokens
                )
                
                # Use property setters to handle JSON serialization
                paragraph.bbox_dict = seg_para.bbox
                paragraph.char_span_dict = seg_para.char_span
                
                paragraphs.append(paragraph)
                db.session.add(paragraph)
            
            # Commit transaction
            db.session.commit()
            
            logger.info(f"Saved document {doc_id} with {len(paragraphs)} paragraphs using {enhanced_result.strategy_used.value} strategy")
            return document, paragraphs
            
        except Exception as e:
            logger.error(f"Error saving enhanced result to database: {e}")
            db.session.rollback()
            return None, []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and all associated data including physical files.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get document
            document = self.document_repo.get_by_id(doc_id)
            if not document:
                logger.warning(f"Document {doc_id} not found for deletion")
                return False

            # Delete physical file if it exists
            if document.file_path and os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                    logger.info(f"Deleted physical file: {document.file_path}")
                except Exception as e:
                    logger.error(f"Error deleting physical file {document.file_path}: {e}")
                    # Don't fail the entire deletion for file deletion error

            # Delete embeddings if embedding service is available
            if self.embedding_service:
                self.embedding_service.delete_embeddings_for_document(doc_id)

            # Delete from database (cascades to paragraphs and embeddings)
            db.session.delete(document)
            db.session.commit()

            logger.info(f"Deleted document {doc_id} and all associated data")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            db.session.rollback()
            return False
    
    def get_ingestion_status(self, job_id: str) -> Optional[IngestionProgress]:
        """
        Get the current status of an ingestion job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            IngestionProgress if job exists, None otherwise
        """
        # In a production system, this would query a job queue or cache
        # For now, return None as jobs are processed synchronously
        return None
    
    def list_failed_documents(self) -> List[Dict[str, Any]]:
        """
        List documents that failed during ingestion.
        
        Returns:
            List of failed document information
        """
        # In a production system, this would query a failed jobs table
        # For now, return empty list
        return []
    
    def retry_failed_document(self, job_id: str) -> IngestionResult:
        """
        Retry ingestion of a failed document.
        
        Args:
            job_id: Job ID to retry
            
        Returns:
            IngestionResult with retry outcome
        """
        # In a production system, this would retrieve the original PDF
        # and retry the ingestion process
        return IngestionResult(
            success=False,
            error_message="Retry functionality not implemented yet"
        )
    
