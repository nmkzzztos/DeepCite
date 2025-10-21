"""
PDF parsing service using PyMuPDF for text extraction with bbox coordinates.
"""
import fitz  # PyMuPDF
import hashlib
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Represents a bounding box with coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2
        }


@dataclass
class TextBlock:
    """Represents a text block with content and positioning."""
    text: str
    bbox: BoundingBox
    page_num: int
    block_idx: int
    font_size: float
    font_name: str
    flags: int  # Font flags (bold, italic, etc.)
    
    @property
    def is_bold(self) -> bool:
        """Check if text is bold based on font flags."""
        return bool(self.flags & 2**4)
    
    @property
    def is_italic(self) -> bool:
        """Check if text is italic based on font flags."""
        return bool(self.flags & 2**1)


@dataclass
class DocumentMetadata:
    """Document metadata extracted from PDF."""
    title: Optional[str] = None
    authors: List[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []


@dataclass
class TocEntry:
    """Table of Contents entry."""
    level: int
    title: str
    page: int
    title_clean: Optional[str] = None
    
    def __post_init__(self):
        if self.title_clean is None:
            # Clean title by removing numbering
            import re
            cleaned = re.sub(r'^\d+(\.\d+)*\.?\s*', '', self.title)
            cleaned = re.sub(r'^[A-Z](\.\d+)+\.?\s*', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            self.title_clean = cleaned if cleaned else self.title


@dataclass
class ParsedDocument:
    """Complete parsed document with metadata and text blocks."""
    metadata: DocumentMetadata
    text_blocks: List[TextBlock]
    page_count: int
    file_hash: str
    toc_entries: List[TocEntry] = None
    
    def __post_init__(self):
        if self.toc_entries is None:
            self.toc_entries = []


class PDFParser:
    """PDF parser using PyMuPDF for text extraction with bbox coordinates."""
    
    def __init__(self):
        self.min_font_size = 6.0  # Minimum font size to consider
        self.max_font_size = 72.0  # Maximum font size to consider
    
    def parse_document(self, pdf_path: str) -> ParsedDocument:
        """
        Parse a PDF document and extract text blocks with coordinates.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ParsedDocument with metadata and text blocks
        """
        # Calculate file hash
        file_hash = self._calculate_file_hash(pdf_path)
        
        # Open PDF document
        doc = fitz.open(pdf_path)
        
        try:
            # Extract metadata
            metadata = self._extract_metadata(doc)
            
            # Extract text blocks from all pages
            text_blocks = []
            for page_num in range(len(doc)):
                page_blocks = self._extract_page_text_blocks(doc[page_num], page_num)
                text_blocks.extend(page_blocks)
            
            # Extract table of contents
            toc_entries = self._extract_toc(doc)
            
            return ParsedDocument(
                metadata=metadata,
                text_blocks=text_blocks,
                page_count=len(doc),
                file_hash=file_hash,
                toc_entries=toc_entries
            )
        
        finally:
            doc.close()
    
    def parse_document_from_bytes(self, pdf_bytes: bytes) -> ParsedDocument:
        """
        Parse a PDF document from bytes and extract text blocks with coordinates.
        
        Args:
            pdf_bytes: PDF file content as bytes
            
        Returns:
            ParsedDocument with metadata and text blocks
        """
        # Calculate file hash
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        
        # Open PDF document from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        try:
            # Extract metadata
            metadata = self._extract_metadata(doc)
            
            # Extract text blocks from all pages
            text_blocks = []
            for page_num in range(len(doc)):
                page_blocks = self._extract_page_text_blocks(doc[page_num], page_num)
                text_blocks.extend(page_blocks)
            
            # Extract table of contents
            toc_entries = self._extract_toc(doc)
            
            return ParsedDocument(
                metadata=metadata,
                text_blocks=text_blocks,
                page_count=len(doc),
                file_hash=file_hash,
                toc_entries=toc_entries
            )
        
        finally:
            doc.close()
    
    def _calculate_file_hash(self, pdf_path: str) -> str:
        """Calculate SHA256 hash of the PDF file."""
        hash_sha256 = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _extract_metadata(self, doc: fitz.Document) -> DocumentMetadata:
        """Extract metadata from PDF document."""
        metadata_dict = doc.metadata
        
        # Extract title
        title = metadata_dict.get('title', '').strip()
        if not title:
            title = None
        
        # Extract authors - try different fields
        authors = []
        author_field = metadata_dict.get('author', '').strip()
        if author_field:
            # Split by common separators
            authors = self._parse_authors(author_field)
        
        return DocumentMetadata(
            title=title,
            authors=authors,
            subject=metadata_dict.get('subject', '').strip() or None,
            creator=metadata_dict.get('creator', '').strip() or None,
            producer=metadata_dict.get('producer', '').strip() or None,
            creation_date=metadata_dict.get('creationDate', '').strip() or None,
            modification_date=metadata_dict.get('modDate', '').strip() or None,
            page_count=len(doc)
        )
    
    def _parse_authors(self, author_field: str) -> List[str]:
        """Parse author field into individual authors."""
        # Common separators for multiple authors
        separators = [';', ',', ' and ', ' & ', '\n']
        
        authors = [author_field]
        for sep in separators:
            new_authors = []
            for author in authors:
                new_authors.extend([a.strip() for a in author.split(sep)])
            authors = new_authors
        
        # Filter out empty strings and clean up
        authors = [author for author in authors if author and len(author) > 1]
        return authors[:10]  # Limit to 10 authors max
    
    def _extract_page_text_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extract text blocks from a single page with bbox coordinates."""
        text_blocks = []
        
        # Get text blocks with detailed information
        blocks = page.get_text("dict")
        
        block_idx = 0
        for block in blocks.get("blocks", []):
            if "lines" not in block:
                continue  # Skip image blocks
            
            # Process each line in the block
            for line in block["lines"]:
                line_text_parts = []
                line_bbox = None
                font_info = None
                
                # Collect spans (text runs with same formatting)
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    
                    # Get font information
                    font_size = span.get("size", 0)
                    font_name = span.get("font", "")
                    flags = span.get("flags", 0)
                    
                    # Filter by font size
                    if font_size < self.min_font_size or font_size > self.max_font_size:
                        continue
                    
                    line_text_parts.append(text)
                    
                    # Use first span's font info for the line
                    if font_info is None:
                        font_info = (font_size, font_name, flags)
                    
                    # Expand bounding box to include this span
                    span_bbox = span.get("bbox")
                    if span_bbox and len(span_bbox) == 4:
                        if line_bbox is None:
                            line_bbox = list(span_bbox)
                        else:
                            line_bbox[0] = min(line_bbox[0], span_bbox[0])  # x1
                            line_bbox[1] = min(line_bbox[1], span_bbox[1])  # y1
                            line_bbox[2] = max(line_bbox[2], span_bbox[2])  # x2
                            line_bbox[3] = max(line_bbox[3], span_bbox[3])  # y2
                
                # Create text block if we have content
                if line_text_parts and line_bbox and font_info:
                    combined_text = " ".join(line_text_parts).strip()
                    if len(combined_text) > 0:
                        text_block = TextBlock(
                            text=combined_text,
                            bbox=BoundingBox(
                                x1=line_bbox[0],
                                y1=line_bbox[1],
                                x2=line_bbox[2],
                                y2=line_bbox[3]
                            ),
                            page_num=page_num + 1,  # 1-based page numbering
                            block_idx=block_idx,
                            font_size=font_info[0],
                            font_name=font_info[1],
                            flags=font_info[2]
                        )
                        text_blocks.append(text_block)
                        block_idx += 1
        
        # Sort blocks for proper reading order (handles multi-column layouts)
        text_blocks = self._sort_blocks_reading_order(text_blocks)
        
        return text_blocks
    
    def _sort_blocks_reading_order(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Sort text blocks in proper reading order, handling multi-column layouts.
        
        Args:
            blocks: List of text blocks to sort
            
        Returns:
            Sorted list of text blocks
        """
        if not blocks:
            return blocks
        
        # Calculate page dimensions
        page_width = max(block.bbox.x2 for block in blocks) - min(block.bbox.x1 for block in blocks)
        page_height = max(block.bbox.y2 for block in blocks) - min(block.bbox.y1 for block in blocks)
        
        # Detect columns using k-means-like clustering on X positions
        x_positions = [block.bbox.x1 for block in blocks]
        x_positions.sort()
        
        # Simple column detection: look for significant gaps in X positions
        columns = []
        current_column_start = x_positions[0]
        gap_threshold = page_width * 0.2  # 20% of page width
        
        for i in range(1, len(x_positions)):
            if x_positions[i] - x_positions[i-1] > gap_threshold:
                # Found a significant gap, likely a column boundary
                columns.append(current_column_start)
                current_column_start = x_positions[i]
        columns.append(current_column_start)
        
        # If we detected multiple columns, group blocks by column
        if len(columns) > 1:
            # Group blocks by column
            column_blocks = [[] for _ in columns]
            for block in blocks:
                # Find the closest column
                best_column = 0
                min_distance = abs(block.bbox.x1 - columns[0])
                for i, col_x in enumerate(columns):
                    distance = abs(block.bbox.x1 - col_x)
                    if distance < min_distance:
                        min_distance = distance
                        best_column = i
                column_blocks[best_column].append(block)
            
            # Sort each column by Y position
            for col_blocks in column_blocks:
                col_blocks.sort(key=lambda b: b.bbox.y1)
            
            # Merge columns by interleaving based on Y position
            sorted_blocks = []
            column_indices = [0] * len(column_blocks)
            
            while any(idx < len(column_blocks[i]) for i, idx in enumerate(column_indices)):
                # Find the block with the smallest Y position among all columns
                best_block = None
                best_column = -1
                best_y = float('inf')
                
                for col_idx, blocks_in_col in enumerate(column_blocks):
                    if column_indices[col_idx] < len(blocks_in_col):
                        block = blocks_in_col[column_indices[col_idx]]
                        if block.bbox.y1 < best_y:
                            best_y = block.bbox.y1
                            best_block = block
                            best_column = col_idx
                
                if best_block:
                    sorted_blocks.append(best_block)
                    column_indices[best_column] += 1
        else:
            # Single column - group by line and sort within lines
            line_groups = []
            current_group = []
            current_y = None
            line_tolerance = 5.0  # pixels
            
            # First sort by Y coordinate
            blocks_by_y = sorted(blocks, key=lambda b: b.bbox.y1)
            
            for block in blocks_by_y:
                if current_y is None or abs(block.bbox.y1 - current_y) <= line_tolerance:
                    current_group.append(block)
                    current_y = block.bbox.y1 if current_y is None else current_y
                else:
                    if current_group:
                        line_groups.append(current_group)
                    current_group = [block]
                    current_y = block.bbox.y1
            
            if current_group:
                line_groups.append(current_group)
            
            # Sort each line group by X coordinate (left to right)
            sorted_blocks = []
            for group in line_groups:
                group_sorted = sorted(group, key=lambda b: b.bbox.x1)
                sorted_blocks.extend(group_sorted)
        
        return sorted_blocks
    
    def extract_document_title_from_content(self, text_blocks: List[TextBlock]) -> Optional[str]:
        """
        Extract document title from text blocks using heuristics.
        
        This is a fallback when metadata doesn't contain a title.
        """
        if not text_blocks:
            return None
        
        # Look for title in first page, typically largest font size
        first_page_blocks = [block for block in text_blocks if block.page_num == 1]
        if not first_page_blocks:
            return None
        
        # Sort blocks by font size (descending) and then by position
        sorted_blocks = sorted(first_page_blocks, key=lambda b: (-b.font_size, b.bbox.y1))
        
        # Take first few blocks as potential title, considering different font sizes
        title_parts = []
        for block in sorted_blocks[:5]:  # Max 5 blocks for title
            text = block.text.strip()
            
            # Check for section headers first (regardless of length)
            if text.lower() in ['abstract', 'introduction', 'references', 'keywords']:
                break  # Stop at section headers
            
            # Skip if text looks like header/footer or page numbers
            if len(text) < 10 or len(text) > 200:
                continue
            if re.match(r'^\d+$', text):  # Skip page numbers
                continue
            
            title_parts.append(text)
            
            # If we have enough content and this block is significantly smaller font, stop
            if len(title_parts) > 1 and len(" ".join(title_parts)) >= 30:
                current_font = block.font_size
                first_font = sorted_blocks[0].font_size
                if current_font < first_font - 2.0:  # Significant font size drop
                    break
        
        if title_parts:
            title = " ".join(title_parts).strip()
            # Clean up title
            title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
            return title if len(title) >= 10 else None
        
        return None
    
    def _extract_toc(self, doc: fitz.Document) -> List[TocEntry]:
        """
        Extract table of contents from PDF document.
        
        Args:
            doc: PyMuPDF document
            
        Returns:
            List of TOC entries
        """
        toc_entries = []
        
        try:
            # Extract TOC using PyMuPDF
            toc_data = doc.get_toc(simple=False)  # Full format: [level, title, page, dest]
            
            if not toc_data:
                # Try simple format as fallback
                toc_data = doc.get_toc(simple=True)  # Simple format: [level, title, page]
                if toc_data:
                    # Convert to expected format
                    toc_data = [(level, title, page, None) for level, title, page in toc_data]
            
            # Process each TOC entry
            for entry in toc_data:
                if len(entry) >= 3:
                    level, title, page = entry[0], entry[1], entry[2]
                    
                    # Skip invalid entries
                    if not title or page < 1:
                        continue
                    
                    # Clean title
                    title = title.strip()
                    if not title:
                        continue
                    
                    toc_entry = TocEntry(
                        level=level,
                        title=title,
                        page=page
                    )
                    toc_entries.append(toc_entry)
                    
        except Exception as e:
            logger.warning(f"Failed to extract TOC: {e}")
        
        logger.info(f"Extracted {len(toc_entries)} TOC entries")
        return toc_entries