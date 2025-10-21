"""
Text segmentation service for creating coherent paragraphs with stable IDs.
"""
import hashlib
import re
import statistics
import unicodedata
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

from .pdf_content_extractor import TextBlock, ParsedDocument, TocEntry

logger = logging.getLogger(__name__)


@dataclass
class SegmentedParagraph:
    """Represents a segmented paragraph with metadata."""
    stable_id: str
    doc_id: str
    page: int
    para_idx: int
    text: str
    bbox: Dict[str, float]  # {x1, y1, x2, y2}
    char_span: Optional[Dict[str, int]]  # {start, end}
    section_path: Optional[str]
    paragraph_type: str  # 'paragraph', 'figure_caption', 'table', 'header', 'footer'
    tokens: int
    font_size: float
    is_bold: bool
    is_italic: bool


class TextSegmenter:
    """
    Text segmentation service that creates coherent paragraphs from text blocks
    with stable ID generation and section path extraction.
    """
    
    def __init__(self):
        """Initialize the text segmenter with configuration parameters."""
        # Layout-based segmentation parameters
        self.min_paragraph_length = 10  # Minimum characters for a paragraph
        self.default_max_line_gap = 5.0  # Default maximum vertical gap (will be adaptive)
        self.header_font_threshold = 2.0  # Font size difference to consider as header
        self.min_header_length = 3  # Minimum length for header text
        self.max_header_length = 200  # Maximum length for header text
        
        # Adaptive parameters (will be set per page)
        self._dyn_max_line_gap = self.default_max_line_gap
        self._median_font = 11.0
        self._median_line_height = 10.0
        
        # Figure and table detection patterns (enhanced for multiple languages)
        self.figure_patterns = [
            r'^fig(?:ure)?\s*\d+',
            r'^figure\s+\d+',
            r'^\d+\.\s*fig(?:ure)?',
            r'fig\.\s*\d+',
            r'^abb(?:ildung)?\s*\d+',  # German
            r'^abbildung\s+\d+',
        ]
        self.table_patterns = [
            r'^table\s*\d+',
            r'^tab(?:le)?\s*\d+',
            r'^\d+\.\s*table',
            r'tab\.\s*\d+',
            r'^tabelle\s*\d+',  # German
        ]
        
        # List item patterns
        self.list_patterns = [
            r'^[•\u2022\u25E6\u25AA\-\*]\s+',  # Bullet points
            r'^\(?[ivxlcdm]+\)\s+',             # Roman numerals (i), (ii)
            r'^\(?[A-Za-z]\)\s+',               # Letters (a), a)
            r'^\d+[\.\)]\s+'                    # Numbers 1., 1)
        ]
        
        # Common section headers to help with path extraction
        self.section_headers = {
            'abstract', 'introduction', 'background', 'related work', 'methodology',
            'methods', 'approach', 'implementation', 'results', 'evaluation',
            'discussion', 'conclusion', 'conclusions', 'future work', 'references',
            'bibliography', 'acknowledgments', 'acknowledgements', 'appendix',
            'literature review', 'state of the art', 'problem statement',
            'system design', 'architecture', 'experimental setup', 'experiments',
            'analysis', 'findings', 'limitations', 'contributions', 'summary',
            'overview', 'motivation', 'objectives', 'scope', 'definitions',
            'terminology', 'notation', 'preliminaries', 'case study',
            'use case', 'scenario', 'example', 'proof', 'theorem', 'lemma',
            'algorithm', 'procedure', 'protocol', 'framework', 'model',
            'comparison', 'performance', 'benchmarks', 'validation',
            'verification', 'testing', 'simulation', 'implementation details'
        }
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent processing.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        # Unicode normalization
        text = unicodedata.normalize('NFKC', text)
        
        # Replace common ligatures
        text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
        text = text.replace('ﬀ', 'ff').replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def _fix_hyphens(self, text: str) -> str:
        """
        Fix word hyphenation artifacts.
        
        Args:
            text: Input text
            
        Returns:
            Text with fixed hyphenation
        """
        # Fix "auto-\nmatic" and "auto- matic" → "automatic"
        text = re.sub(r'(\w+)-\s+(\w+)', 
                     lambda m: m.group(1) + m.group(2) 
                     if m.group(2)[0].islower() else m.group(0), text)
        return text
    
    def _calculate_page_stats(self, blocks: List[TextBlock]) -> Tuple[float, float, float]:
        """
        Calculate adaptive statistics for a page.
        
        Args:
            blocks: Text blocks on the page
            
        Returns:
            Tuple of (median_line_height, median_font_size, median_gap)
        """
        if not blocks:
            return 10.0, 11.0, 3.0
        
        # Calculate line heights
        line_heights = [block.bbox.y2 - block.bbox.y1 for block in blocks]
        
        # Calculate font sizes
        font_sizes = [block.font_size for block in blocks]
        
        # Calculate gaps between consecutive blocks on same page
        gaps = []
        sorted_blocks = sorted(blocks, key=lambda b: (b.bbox.y1, b.bbox.x1))
        for i in range(len(sorted_blocks) - 1):
            curr_block = sorted_blocks[i]
            next_block = sorted_blocks[i + 1]
            if next_block.page_num == curr_block.page_num:
                gap = next_block.bbox.y1 - curr_block.bbox.y2
                if gap > 0:
                    gaps.append(gap)
        
        # Calculate medians
        median_height = statistics.median(line_heights) if line_heights else 10.0
        median_font = statistics.median(font_sizes) if font_sizes else 11.0
        median_gap = statistics.median(gaps) if gaps else 3.0
        
        return median_height, median_font, median_gap
    
    def _detect_repeating_bands(self, pages_blocks: Dict[int, List[TextBlock]], 
                               top_threshold: float = 60, bottom_threshold: float = 60,
                               min_pages: int = 3) -> Set[str]:
        """
        Detect repeating headers/footers across pages.
        
        Args:
            pages_blocks: Blocks grouped by page
            top_threshold: Y coordinate threshold for headers
            bottom_threshold: Y coordinate threshold from bottom for footers
            min_pages: Minimum pages a text must appear on to be considered repeating
            
        Returns:
            Set of normalized texts that are repeating bands
        """
        text_counter = defaultdict(int)
        
        for page_num, blocks in pages_blocks.items():
            if not blocks:
                continue
                
            # Calculate page height
            page_height = max(block.bbox.y2 for block in blocks) if blocks else 800
            
            for block in blocks:
                # Check if block is in header or footer area
                is_header = block.bbox.y1 < top_threshold
                is_footer = block.bbox.y2 > (page_height - bottom_threshold)
                
                if is_header or is_footer:
                    normalized_text = self._normalize_text(block.text).lower()
                    # Only consider texts of reasonable length
                    if 3 <= len(normalized_text) <= 200:
                        text_counter[normalized_text] += 1
        
        # Return texts that appear on multiple pages
        return {text for text, count in text_counter.items() if count >= min_pages}
    
    def _build_toc_page_map(self, toc_entries: List[TocEntry]) -> List[Dict[str, any]]:
        """
        Build page-based section mapping from TOC entries.
        
        Args:
            toc_entries: List of TOC entries from PDF
            
        Returns:
            List of section mappings with page ranges
        """
        if not toc_entries:
            return []
        
        toc_map = []
        
        # Process each TOC entry and determine its page range
        for i, entry in enumerate(toc_entries):
            # Determine end page (start of next entry or end of document)
            end_page = toc_entries[i + 1].page - 1 if i + 1 < len(toc_entries) else 10000
            
            section_info = {
                'level': entry.level,
                'title': entry.title,
                'title_clean': entry.title_clean or entry.title,
                'start_page': entry.page,
                'end_page': end_page
            }
            toc_map.append(section_info)
        
        logger.info(f"Built TOC page map with {len(toc_map)} sections")
        return toc_map
    
    def _get_section_from_toc(self, page_num: int, toc_map: List[Dict[str, any]]) -> Optional[str]:
        """
        Get section title for a page from TOC mapping.
        
        Args:
            page_num: Page number (1-based)
            toc_map: TOC page mapping
            
        Returns:
            Section title or None
        """
        for section in toc_map:
            if section['start_page'] <= page_num <= section['end_page']:
                return section['title_clean']
        return None
    
    def segment_document(
        self, 
        parsed_doc: ParsedDocument, 
        doc_id: str = None
    ) -> List[SegmentedParagraph]:
        """
        Segment a parsed document into coherent paragraphs.
        
        Args:
            parsed_doc: Document parsed by PDFParser
            doc_id: Document ID for stable ID generation
            
        Returns:
            List of segmented paragraphs with metadata
        """
        if not doc_id:
            doc_id = parsed_doc.file_hash
        
        # Group text blocks by page for processing
        pages_blocks = self._group_blocks_by_page(parsed_doc.text_blocks)
        
        # Detect and filter repeating headers/footers
        repeating_bands = self._detect_repeating_bands(pages_blocks)
        logger.info(f"Detected {len(repeating_bands)} repeating text bands to filter")
        
        # Filter out repeating bands from all pages
        filtered_pages_blocks = {}
        for page_num, blocks in pages_blocks.items():
            filtered_blocks = []
            for block in blocks:
                normalized_text = self._normalize_text(block.text).lower()
                if normalized_text not in repeating_bands:
                    filtered_blocks.append(block)
                else:
                    logger.debug(f"Filtered repeating band: {normalized_text[:50]}...")
            filtered_pages_blocks[page_num] = filtered_blocks
        
        # No GROBID structure available, use empty section map
        section_map = {}
        
        # Build TOC page mapping
        toc_map = self._build_toc_page_map(parsed_doc.toc_entries)
        
        # Process each page with global context
        all_paragraphs = []
        global_para_idx = 0
        current_section_path = None  # Track section across pages
        
        for page_num in sorted(filtered_pages_blocks.keys()):
            page_blocks = filtered_pages_blocks[page_num]
            
            if not page_blocks:
                continue
            
            # Blocks are already sorted by PDFParser, no need to re-sort
            sorted_blocks = page_blocks
            
            # Segment blocks into paragraphs
            page_paragraphs, current_section_path = self._segment_page_blocks_with_context(
                sorted_blocks, 
                page_num, 
                doc_id,
                section_map,
                toc_map,
                global_para_idx,
                current_section_path
            )
            
            all_paragraphs.extend(page_paragraphs)
            global_para_idx += len(page_paragraphs)
        
        # Post-process to fix any remaining null section paths
        self._fix_null_section_paths(all_paragraphs)
        
        # Post-process to combine pre-Abstract content
        all_paragraphs = self._combine_pre_abstract_content(all_paragraphs)
        
        # Post-process to remove duplicates
        all_paragraphs = self._remove_duplicate_paragraphs(all_paragraphs)
        
        # Post-process to merge short paragraphs with previous ones
        all_paragraphs = self._merge_short_paragraphs(all_paragraphs)
        
        return all_paragraphs
    

    def _group_blocks_by_page(self, text_blocks: List[TextBlock]) -> Dict[int, List[TextBlock]]:
        """Group text blocks by page number."""
        pages = defaultdict(list)
        for block in text_blocks:
            pages[block.page_num].append(block)
        return dict(pages)
    
    def _build_section_map(self) -> Dict[str, str]:
        """
        Build a mapping from text content to section paths.
        Since GROBID is removed, this returns an empty map.
        
        Returns:
            Empty dictionary (no GROBID structure available)
        """
        return {}
    
    def _build_section_path(self, section) -> str:
        """Build hierarchical section path."""
        if section.section_number and section.title:
            return f"{section.section_number} {section.title}"
        elif section.title:
            return section.title
        else:
            return f"Section {section.level}"
    
    def _extract_content_snippets(self, content: str, snippet_length: int = 50) -> List[str]:
        """Extract representative snippets from section content for matching."""
        if not content or len(content) < snippet_length:
            return []
        
        # Take first snippet and a few others from the content
        snippets = []
        
        # First snippet
        first_snippet = content[:snippet_length].lower().strip()
        if first_snippet:
            snippets.append(first_snippet)
        
        # Additional snippets from middle and end
        if len(content) > snippet_length * 3:
            mid_start = len(content) // 2
            mid_snippet = content[mid_start:mid_start + snippet_length].lower().strip()
            if mid_snippet:
                snippets.append(mid_snippet)
        
        return snippets
    
    def _segment_page_blocks(
        self, 
        blocks: List[TextBlock], 
        page_num: int, 
        doc_id: str,
        section_map: Dict[str, str],
        start_para_idx: int
    ) -> List[SegmentedParagraph]:
        """
        Segment text blocks on a single page into paragraphs.
        
        Args:
            blocks: Sorted text blocks for the page
            page_num: Page number
            doc_id: Document ID
            section_map: Mapping from content to section paths
            start_para_idx: Starting paragraph index for this page
            
        Returns:
            List of segmented paragraphs for the page
        """
        if not blocks:
            return []
        
        paragraphs = []
        current_paragraph_blocks = []
        current_section_path = None
        para_idx = start_para_idx
        
        # Use adaptive page statistics for segmentation
        # (self._median_font replaced with median-based calculations)
        
        # Track section headers to maintain context
        last_header_block = None
        
        for i, block in enumerate(blocks):
            # Check if this is a section header first
            is_header = self._is_section_header(block, self._median_font)
            
            # Determine if this block should start a new paragraph
            should_start_new = self._should_start_new_paragraph(
                block, current_paragraph_blocks, self._median_font
            )
            
            # Always start new paragraph for headers
            if is_header:
                should_start_new = True
            
            if should_start_new and current_paragraph_blocks:
                # Finalize current paragraph
                paragraph = self._create_paragraph_from_blocks(
                    current_paragraph_blocks,
                    page_num,
                    para_idx,
                    doc_id,
                    current_section_path
                )
                if paragraph:
                    paragraphs.append(paragraph)
                    para_idx += 1
                
                current_paragraph_blocks = []
            
            # Update section path if this is a header
            if is_header:
                # Prioritize TOC section, then GROBID mapping
                new_section_path = self._extract_section_path(block, section_map)
                if new_section_path:
                    current_section_path = new_section_path
                    last_header_block = block
            elif last_header_block and not current_section_path:
                # If we haven't set a section path yet, try to use the last header
                fallback_section = self._extract_section_path(last_header_block, section_map)
                current_section_path = fallback_section
            
            # Add block to current paragraph
            current_paragraph_blocks.append(block)
        
        # Finalize last paragraph
        if current_paragraph_blocks:
            paragraph = self._create_paragraph_from_blocks(
                current_paragraph_blocks,
                page_num,
                para_idx,
                doc_id,
                current_section_path
            )
            if paragraph:
                paragraphs.append(paragraph)
        
        return paragraphs
    
    def _segment_page_blocks_with_context(
        self, 
        blocks: List[TextBlock], 
        page_num: int, 
        doc_id: str,
        section_map: Dict[str, str],
        toc_map: List[Dict[str, any]],
        start_para_idx: int,
        inherited_section_path: Optional[str]
    ) -> Tuple[List[SegmentedParagraph], Optional[str]]:
        """
        Segment text blocks on a single page into paragraphs with global context.
        
        Args:
            blocks: Sorted text blocks for the page
            page_num: Page number
            doc_id: Document ID
            section_map: Mapping from content to section paths
            start_para_idx: Starting paragraph index for this page
            inherited_section_path: Section path from previous page
            
        Returns:
            Tuple of (paragraphs, final_section_path)
        """
        if not blocks:
            return [], inherited_section_path
        
        paragraphs = []
        current_paragraph_blocks = []
        
        # Try to get section from TOC first, then fall back to inherited
        toc_section = self._get_section_from_toc(page_num, toc_map)
        current_section_path = toc_section or inherited_section_path
        
        para_idx = start_para_idx
        
        # Calculate adaptive page statistics
        median_height, median_font, median_gap = self._calculate_page_stats(blocks)
        self._dyn_max_line_gap = max(0.35 * median_height, 2.0)
        self._median_font = median_font
        self._median_line_height = median_height
        
        logger.debug(f"Page {page_num} stats: median_font={median_font:.1f}, "
                    f"median_gap={median_gap:.1f}, dyn_max_gap={self._dyn_max_line_gap:.1f}")
        
        # Track section headers to maintain context
        last_header_block = None
        
        for i, block in enumerate(blocks):
            # Check if this is a section header first
            is_header = self._is_section_header(block, self._median_font)
            
            # Determine if this block should start a new paragraph
            should_start_new = self._should_start_new_paragraph(
                block, current_paragraph_blocks, self._median_font
            )
            
            # Always start new paragraph for headers
            if is_header:
                should_start_new = True
            
            if should_start_new and current_paragraph_blocks:
                # Finalize current paragraph
                paragraph = self._create_paragraph_from_blocks(
                    current_paragraph_blocks,
                    page_num,
                    para_idx,
                    doc_id,
                    current_section_path
                )
                if paragraph and self._should_save_paragraph(paragraph):
                    paragraphs.append(paragraph)
                    para_idx += 1
                
                current_paragraph_blocks = []
            
            # Update section path if this is a header
            if is_header:
                # Prioritize TOC section, then GROBID mapping
                new_section_path = self._extract_section_path(block, section_map)
                if new_section_path:
                    current_section_path = new_section_path
                    last_header_block = block
            elif last_header_block and not current_section_path:
                # If we haven't set a section path yet, try to use the last header
                fallback_section = self._extract_section_path(last_header_block, section_map)
                current_section_path = fallback_section
            
            # Add block to current paragraph
            current_paragraph_blocks.append(block)
        
        # Finalize last paragraph
        if current_paragraph_blocks:
            paragraph = self._create_paragraph_from_blocks(
                current_paragraph_blocks,
                page_num,
                para_idx,
                doc_id,
                current_section_path
            )
            if paragraph and self._should_save_paragraph(paragraph):
                paragraphs.append(paragraph)
        
        return paragraphs, current_section_path
    
    def _fix_null_section_paths(self, paragraphs: List[SegmentedParagraph]) -> None:
        """
        Fix null section paths by propagating from nearby paragraphs.
        
        Args:
            paragraphs: List of segmented paragraphs to fix
        """
        if not paragraphs:
            return
        
        # Forward pass: propagate section paths forward
        current_section = None
        for paragraph in paragraphs:
            if paragraph.section_path:
                current_section = paragraph.section_path
            elif current_section and not paragraph.section_path:
                paragraph.section_path = current_section
        
        # Backward pass: propagate section paths backward for early paragraphs
        current_section = None
        for paragraph in reversed(paragraphs):
            if paragraph.section_path:
                current_section = paragraph.section_path
            elif current_section and not paragraph.section_path:
                # Only propagate backward if it's likely the same section
                # (e.g., within first few paragraphs or similar content)
                if paragraph.para_idx < 5 or self._is_likely_same_section(paragraph, current_section):
                    paragraph.section_path = current_section
    
    def _is_likely_same_section(self, paragraph: SegmentedParagraph, section_path: str) -> bool:
        """
        Determine if a paragraph likely belongs to the given section.
        
        Args:
            paragraph: Paragraph to check
            section_path: Section path to compare against
            
        Returns:
            True if likely the same section
        """
        if not section_path:
            return False
        
        text_lower = paragraph.text.lower()
        section_lower = section_path.lower()
        
        # Check if paragraph text contains section keywords
        section_words = section_lower.split()
        for word in section_words:
            if len(word) > 3 and word in text_lower:
                return True
        
        # Check if it's a continuation pattern (starts with lowercase, no clear header)
        if paragraph.text and paragraph.text[0].islower():
            return True
        
        return False
    
    def _should_start_new_paragraph(
        self, 
        block: TextBlock, 
        current_blocks: List[TextBlock],
        median_font: float
    ) -> bool:
        """
        Determine if a text block should start a new paragraph.
        
        Args:
            block: Current text block
            current_blocks: Blocks in current paragraph
            self._median_font: Average font size on page
            
        Returns:
            True if should start new paragraph
        """
        if not current_blocks:
            return False
        
        last_block = current_blocks[-1]
        
        # Check vertical gap - use adaptive threshold
        vertical_gap = block.bbox.y1 - last_block.bbox.y2
        if vertical_gap > self._dyn_max_line_gap:
            return True
        
        # Check for significant font size change
        font_size_diff = abs(block.font_size - last_block.font_size)
        if font_size_diff > self.header_font_threshold:
            return True
        
        # Check for formatting changes (bold/italic)
        if block.is_bold != last_block.is_bold or block.is_italic != last_block.is_italic:
            # Only start new paragraph if it's a significant formatting change
            if block.is_bold and not last_block.is_bold:  # Becoming bold
                return True
            if not block.is_bold and last_block.is_bold and vertical_gap > 2.0:  # No longer bold with some gap
                return True
        
        # Check for potential section headers
        if self._is_section_header(block, self._median_font):
            return True
        
        # Check for figure/table captions
        if self._is_figure_or_table_caption(block.text):
            return True
        
        # Check for paragraph-like patterns
        text = block.text.strip()
        
        # Check if text starts with typical paragraph starters
        paragraph_starters = [
            r'^[A-Z][a-z].*\.',  # Sentence starting with capital letter
            r'^In\s+',           # "In this paper", "In order to"
            r'^The\s+',          # "The main", "The purpose"
            r'^This\s+',         # "This paper", "This approach"
            r'^We\s+',           # "We present", "We propose"
            r'^Our\s+',          # "Our method", "Our approach"
            r'^However,',        # Transition words
            r'^Therefore,',
            r'^Furthermore,',
            r'^Moreover,',
            r'^Additionally,',
        ]
        
        for pattern in paragraph_starters:
            if re.match(pattern, text) and vertical_gap > 1.0:
                return True
        
        # Check for indentation changes (new paragraph often indented)
        x_diff = abs(block.bbox.x1 - last_block.bbox.x1)
        if x_diff > 10.0 and vertical_gap > 1.0:  # Significant horizontal shift
            return True
        
        return False
    
    def _is_section_header(self, block: TextBlock, median_font: float) -> bool:
        """
        Determine if a text block is likely a section header.
        
        Args:
            block: Text block to check
            self._median_font: Average font size on page
            
        Returns:
            True if likely a section header
        """
        text = block.text.strip()
        text_lower = text.lower()
        
        # Check length constraints
        if len(text) < self.min_header_length or len(text) > self.max_header_length:
            return False
        
        # More flexible font size check - headers can be same size but bold
        font_size_threshold = self._median_font - 0.5  # Allow slightly smaller fonts
        if block.font_size < font_size_threshold:
            return False
        
        # Check for bold formatting OR larger font size
        is_formatted = block.is_bold or block.font_size >= self._median_font + 1.5
        
        # Check against known section headers
        if text_lower in self.section_headers:
            return is_formatted
        
        # Check for partial matches with known headers
        for header in self.section_headers:
            if header in text_lower or text_lower in header:
                return is_formatted
        
        # Check for numbered sections (e.g., "1. Introduction", "2.1 Background")
        if re.match(r'^\d+(\.\d+)*\.?\s+[a-zA-Z]', text):
            return True
        
        # Check for lettered sections (e.g., "A. Introduction", "B.1 Background")
        if re.match(r'^[A-Z](\.\d+)*\.?\s+[a-zA-Z]', text):
            return True
        
        # Check for Roman numerals
        if re.match(r'^[ivxlcdm]+\.?\s+[a-zA-Z]', text, re.IGNORECASE):
            return True
        
        # Check for section-like patterns
        section_patterns = [
            r'^\d+\.\s*[A-Z][a-z]',  # "1. Introduction"
            r'^[A-Z][a-z]+\s+\d+',   # "Section 1"
            r'^[A-Z][a-z]+\s+[A-Z]', # "Related Work"
            r'^[A-Z]{2,}',           # All caps headers
        ]
        
        for pattern in section_patterns:
            if re.match(pattern, text) and is_formatted:
                return True
        
        # Check if text looks like a title (mostly capitalized words)
        words = text.split()
        if len(words) >= 2 and len(words) <= 8:
            capitalized_words = sum(1 for word in words if word[0].isupper() and len(word) > 2)
            if capitalized_words >= len(words) * 0.6 and is_formatted:
                return True
        
        return False
    
    def _is_figure_or_table_caption(self, text: str) -> bool:
        """Check if text is a figure or table caption."""
        text_lower = text.lower().strip()
        
        # Check figure patterns
        for pattern in self.figure_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check table patterns
        for pattern in self.table_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_section_path(self, block: TextBlock, section_map: Dict[str, str]) -> Optional[str]:
        """
        Extract section path for a header block.
        
        Args:
            block: Text block (potential header)
            section_map: Mapping from content to section paths
            
        Returns:
            Section path or None
        """
        text = block.text.strip()
        text_lower = text.lower()
        
        # Check direct mapping from section map
        if text_lower in section_map:
            return section_map[text_lower]
        
        # Check for partial matches (more conservative)
        for key, path in section_map.items():
            # Require minimum overlap and reasonable length match
            if len(key) >= 5 and len(text_lower) >= 5:
                # Check for substantial overlap
                if (key in text_lower and len(key) >= len(text_lower) * 0.6) or \
                   (text_lower in key and len(text_lower) >= len(key) * 0.6):
                    return path
        
        # Clean up the text for section path
        cleaned_text = self._clean_section_title(text)
        
        # Use the cleaned text as section path
        return cleaned_text if cleaned_text else text
    
    def _clean_section_title(self, title: str) -> str:
        """
        Clean section title by removing numbering and normalizing format.
        Preserves hierarchical structure for better duplicate detection.
        
        Args:
            title: Raw section title
            
        Returns:
            Cleaned section title
        """
        original_title = title.strip()
        
        # Remove leading numbers and dots (e.g., "1.2.3 Title" -> "Title")
        cleaned = re.sub(r'^\d+(\.\d+)*\.?\s*', '', title)
        
        # Remove leading single letters with dots only if followed by numbers (e.g., "A.1 Title" -> "Title")
        # This prevents removing the first letter of actual titles like "Model Architecture"
        cleaned = re.sub(r'^[A-Z](\.\d+)+\.?\s*', '', cleaned)
        
        # Remove Roman numerals with dots/spaces (e.g., "IV. Title" -> "Title")
        cleaned = re.sub(r'^[ivxlcdm]+\.?\s*', '', cleaned, re.IGNORECASE)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # If cleaning removed everything, use original title
        if not cleaned or len(cleaned) < 2:
            cleaned = original_title
        
        # Capitalize first letter of each word for consistency
        if cleaned:
            words = cleaned.split()
            # Don't capitalize small words unless they're the first word
            small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'of', 'on', 'or', 'the', 'to', 'up', 'with'}
            capitalized_words = []
            for i, word in enumerate(words):
                if i == 0 or word.lower() not in small_words:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.lower())
            cleaned = ' '.join(capitalized_words)
        
        return cleaned
    
    def _create_paragraph_from_blocks(
        self,
        blocks: List[TextBlock],
        page_num: int,
        para_idx: int,
        doc_id: str,
        section_path: Optional[str]
    ) -> Optional[SegmentedParagraph]:
        """
        Create a segmented paragraph from a list of text blocks.
        
        Args:
            blocks: Text blocks to combine
            page_num: Page number
            para_idx: Paragraph index
            doc_id: Document ID
            section_path: Section path for the paragraph
            
        Returns:
            SegmentedParagraph or None if invalid
        """
        if not blocks:
            return None
        
        # Combine text from all blocks with normalization
        raw_text = " ".join(block.text.strip() for block in blocks).strip()
        combined_text = self._fix_hyphens(self._normalize_text(raw_text))
        
        # Skip if too short
        if len(combined_text) < self.min_paragraph_length:
            return None
        
        # Calculate combined bounding box
        min_x1 = min(block.bbox.x1 for block in blocks)
        min_y1 = min(block.bbox.y1 for block in blocks)
        max_x2 = max(block.bbox.x2 for block in blocks)
        max_y2 = max(block.bbox.y2 for block in blocks)
        
        combined_bbox = {
            'x1': min_x1,
            'y1': min_y1,
            'x2': max_x2,
            'y2': max_y2
        }
        
        # Use first block's formatting info
        first_block = blocks[0]
        
        # Determine paragraph type
        paragraph_type = self._classify_paragraph_type(combined_text, first_block)
        
        # Generate stable ID
        stable_id = self._generate_stable_id(
            doc_id, page_num, combined_bbox, combined_text
        )
        
        # Estimate token count (rough approximation)
        tokens = self._estimate_token_count(combined_text)
        
        return SegmentedParagraph(
            stable_id=stable_id,
            doc_id=doc_id,
            page=page_num,
            para_idx=para_idx,
            text=combined_text,
            bbox=combined_bbox,
            char_span=None,  # Would need full document text to calculate
            section_path=section_path,
            paragraph_type=paragraph_type,
            tokens=tokens,
            font_size=first_block.font_size,
            is_bold=first_block.is_bold,
            is_italic=first_block.is_italic
        )
    
    def _classify_paragraph_type(self, text: str, first_block: TextBlock) -> str:
        """
        Classify the type of paragraph based on content and formatting.
        
        Args:
            text: Combined paragraph text
            first_block: First text block in paragraph
            
        Returns:
            Paragraph type string
        """
        text_lower = text.lower().strip()
        
        # Check for list items first
        for pattern in self.list_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return 'list_item'
        
        # Check for figure captions
        for pattern in self.figure_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return 'figure_caption'
        
        # Check for table captions
        for pattern in self.table_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return 'table'
        
        # Check for references section content
        if ('references' in text_lower and len(text) < 100) or self._looks_like_reference(text):
            return 'reference_item'
        
        # Check for headers (use adaptive font threshold)
        if (first_block.is_bold and 
            first_block.font_size >= self._median_font + 1.0 and 
            len(text) < self.max_header_length):
            return 'header'
        
        # Check for footers (adaptive bottom threshold)
        page_height = 800  # Default assumption, could be calculated from page blocks
        if (first_block.font_size <= self._median_font - 2 and 
            first_block.bbox.y1 > 0.92 * page_height):
            return 'footer'
        
        # Default to paragraph
        return 'paragraph'
    
    def _looks_like_reference(self, text: str) -> bool:
        """Check if text looks like a bibliographic reference."""
        # Common patterns in references
        ref_patterns = [
            r'\d{4}[\.;]',  # Year
            r'et al\.?',    # Et al
            r'pp?\.\s*\d+', # Page numbers
            r'vol\.?\s*\d+', # Volume
            r'doi:', # DOI
            r'arxiv:', # ArXiv
        ]
        
        text_lower = text.lower()
        matches = sum(1 for pattern in ref_patterns if re.search(pattern, text_lower))
        
        # If multiple reference patterns match, likely a reference
        return matches >= 2
    
    def _generate_stable_id(
        self, 
        doc_id: str, 
        page: int, 
        bbox: Dict[str, float], 
        text: str
    ) -> str:
        """
        Generate stable ID for paragraph using content hashing with grid-based coordinates.
        
        Args:
            doc_id: Document ID
            page: Page number
            bbox: Bounding box coordinates
            text: Paragraph text
            
        Returns:
            Stable paragraph ID
        """
        # Normalize text for stable hashing
        normalized_text = self._normalize_text(text).lower()
        
        # Take first 100 characters for ID generation
        text_snippet = normalized_text[:100]
        
        # Round bbox to grid (reduces sensitivity to small coordinate changes)
        grid_size = 10.0
        grid_bbox = {
            'x1': round(bbox['x1'] / grid_size) * grid_size,
            'y1': round(bbox['y1'] / grid_size) * grid_size,
            'x2': round(bbox['x2'] / grid_size) * grid_size,
            'y2': round(bbox['y2'] / grid_size) * grid_size
        }
        
        # Create hash input with grid-aligned coordinates
        hash_input = f"{doc_id}:{page}:{grid_bbox['x1']:.0f},{grid_bbox['y1']:.0f},{grid_bbox['x2']:.0f},{grid_bbox['y2']:.0f}:{text_snippet}"
        
        # Generate SHA256 hash
        hash_object = hashlib.sha256(hash_input.encode('utf-8'))
        return hash_object.hexdigest()
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple approximation: ~4 characters per token on average
        return max(1, len(text) // 4)
    
    def update_char_spans(self, paragraphs: List[SegmentedParagraph], full_text: str) -> None:
        """
        Update character spans for paragraphs based on full document text.
        
        Args:
            paragraphs: List of segmented paragraphs
            full_text: Full document text
        """
        current_pos = 0
        
        for paragraph in paragraphs:
            # Find paragraph text in full document
            start_pos = full_text.find(paragraph.text, current_pos)
            if start_pos != -1:
                end_pos = start_pos + len(paragraph.text)
                paragraph.char_span = {
                    'start': start_pos,
                    'end': end_pos
                }
                current_pos = end_pos
            else:
                # Fallback: approximate position
                paragraph.char_span = {
                    'start': current_pos,
                    'end': current_pos + len(paragraph.text)
                }
                current_pos += len(paragraph.text)
    
    def _should_save_paragraph(self, paragraph: SegmentedParagraph) -> bool:
        """
        Determine if a paragraph should be saved (not just section titles).
        
        Args:
            paragraph: Paragraph to check
            
        Returns:
            True if paragraph should be saved
        """
        text = paragraph.text.strip()
        
        # Don't save very short paragraphs that are likely just section titles
        if len(text) < self.min_paragraph_length:
            return False
        
        # Don't save paragraphs that are only section headers without content
        if (paragraph.paragraph_type == 'header' and 
            len(text) < 50 and  # Short headers
            not any(char in text for char in '.!?;:')):  # No sentence-ending punctuation
            return False
        
        # Check if it's just a section title (common patterns)
        text_lower = text.lower().strip()
        if (len(text) < 100 and  # Short text
            text_lower in self.section_headers):  # Known section header
            return False
        
        # Don't save standalone section numbers or very short headers
        if (len(text) < 30 and 
            paragraph.paragraph_type == 'header' and
            (re.match(r'^\d+(\.\d+)*\.?\s*$', text) or  # Just numbers like "2.1"
             re.match(r'^[A-Z][a-z]*\s*$', text))):     # Single words like "Introduction"
            return False
        
        # Don't save paragraphs that are just subsection indicators
        subsection_patterns = [
            r'^\d+(\.\d+)+\s*$',  # Just numbers like "2.1.3"
            r'^[A-Z]\.\d+\s*$',   # Like "A.1"
            r'^[ivxlcdm]+\.\s*$', # Roman numerals like "iv."
        ]
        
        for pattern in subsection_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        return True
    
    def _combine_pre_abstract_content(self, paragraphs: List[SegmentedParagraph]) -> List[SegmentedParagraph]:
        """
        Combine all content before the Abstract section into a single paragraph.
        
        Args:
            paragraphs: List of segmented paragraphs
            
        Returns:
            Modified list with pre-Abstract content combined
        """
        if not paragraphs:
            return paragraphs
        
        # Find the Abstract section
        abstract_index = None
        for i, paragraph in enumerate(paragraphs):
            if (paragraph.section_path and 
                'abstract' in paragraph.section_path.lower()):
                abstract_index = i
                break
        
        # If no Abstract found, return as is
        if abstract_index is None or abstract_index == 0:
            return paragraphs
        
        # Combine all paragraphs before Abstract
        pre_abstract_paragraphs = paragraphs[:abstract_index]
        remaining_paragraphs = paragraphs[abstract_index:]
        
        if not pre_abstract_paragraphs:
            return paragraphs
        
        # Create combined paragraph from pre-Abstract content
        combined_text_parts = []
        combined_bbox = None
        first_page = pre_abstract_paragraphs[0].page
        total_tokens = 0
        
        for para in pre_abstract_paragraphs:
            combined_text_parts.append(para.text.strip())
            total_tokens += para.tokens
            
            # Expand bounding box
            if combined_bbox is None:
                combined_bbox = para.bbox.copy()
            else:
                combined_bbox['x1'] = min(combined_bbox['x1'], para.bbox['x1'])
                combined_bbox['y1'] = min(combined_bbox['y1'], para.bbox['y1'])
                combined_bbox['x2'] = max(combined_bbox['x2'], para.bbox['x2'])
                combined_bbox['y2'] = max(combined_bbox['y2'], para.bbox['y2'])
        
        # Create the combined paragraph
        combined_text = ' '.join(combined_text_parts)
        
        # Generate stable ID for combined paragraph
        stable_id = self._generate_stable_id(
            pre_abstract_paragraphs[0].doc_id, 
            first_page, 
            combined_bbox, 
            combined_text
        )
        
        combined_paragraph = SegmentedParagraph(
            stable_id=stable_id,
            doc_id=pre_abstract_paragraphs[0].doc_id,
            page=first_page,
            para_idx=0,  # First paragraph
            text=combined_text,
            bbox=combined_bbox,
            char_span=pre_abstract_paragraphs[0].char_span,  # Use first paragraph's char span
            section_path="Document Header",  # Common name for pre-Abstract content
            paragraph_type='paragraph',
            tokens=total_tokens,
            font_size=pre_abstract_paragraphs[0].font_size,
            is_bold=pre_abstract_paragraphs[0].is_bold,
            is_italic=pre_abstract_paragraphs[0].is_italic
        )
        
        # Adjust para_idx for remaining paragraphs
        for i, para in enumerate(remaining_paragraphs):
            para.para_idx = i + 1
        
        return [combined_paragraph] + remaining_paragraphs
    
    def _remove_duplicate_paragraphs(self, paragraphs: List[SegmentedParagraph]) -> List[SegmentedParagraph]:
        """
        Remove duplicate paragraphs based on normalized text content.
        When duplicates are found, keep the one with the most specific section_path.
        
        Args:
            paragraphs: List of segmented paragraphs
            
        Returns:
            Filtered list without duplicates
        """
        if not paragraphs:
            return paragraphs
        
        seen_hashes = defaultdict(list)
        filtered_paragraphs = []
        
        # Group paragraphs by content hash
        for para in paragraphs:
            # Normalize and hash the text
            normalized_text = self._normalize_text(para.text).lower()
            content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
            seen_hashes[content_hash].append(para)
        
        # Process each group of potentially duplicate paragraphs
        for content_hash, para_list in seen_hashes.items():
            if len(para_list) == 1:
                # No duplicates, keep as is
                filtered_paragraphs.append(para_list[0])
            else:
                # Multiple paragraphs with same content - choose the best one
                best_para = self._choose_best_duplicate(para_list)
                filtered_paragraphs.append(best_para)
                
                if len(para_list) > 1:
                    logger.info(f"Removed {len(para_list) - 1} duplicate paragraphs with text: "
                               f"{para_list[0].text[:50]}...")
        
        # Sort back to original order
        filtered_paragraphs.sort(key=lambda p: (p.page, p.para_idx))
        
        # Re-assign paragraph indices
        for i, para in enumerate(filtered_paragraphs):
            para.para_idx = i
        
        logger.info(f"Removed {len(paragraphs) - len(filtered_paragraphs)} duplicate paragraphs")
        return filtered_paragraphs
    
    def _choose_best_duplicate(self, duplicates: List[SegmentedParagraph]) -> SegmentedParagraph:
        """
        Choose the best paragraph from a list of duplicates.
        Prioritizes more specific section paths and better positioning.
        
        Args:
            duplicates: List of duplicate paragraphs
            
        Returns:
            Best paragraph to keep
        """
        if len(duplicates) == 1:
            return duplicates[0]
        
        # Score each duplicate
        scored_duplicates = []
        for para in duplicates:
            score = 0
            
            # Prefer paragraphs with more specific section paths
            if para.section_path:
                # Count path specificity indicators (numbers, dots, subsections)
                specificity_score = 0

                # Higher score for numbered sections (e.g., "1 Introduction" vs "Introduction")
                if re.match(r'^\d+', para.section_path.strip()):
                    specificity_score += 15

                # Additional score for subsection indicators (e.g., "1.1 Subsection")
                specificity_score += para.section_path.count('.') * 10

                # Score based on length (longer paths are usually more specific)
                specificity_score += min(len(para.section_path), 100)  # Cap at 100

                score += specificity_score
                
                # Avoid generic section names
                generic_sections = ['document header', 'untitled', 'section', 'chapter']
                if not any(generic in para.section_path.lower() for generic in generic_sections):
                    score += 20
            else:
                # Penalize paragraphs without section paths
                score -= 50
            
            # Prefer paragraphs that are not just headers
            if para.paragraph_type != 'header':
                score += 15
            
            # Prefer paragraphs with more content (tokens)
            score += min(para.tokens, 100)  # Cap at 100 to avoid huge bias
            
            # Prefer earlier pages (usually more important content)
            score -= para.page * 0.1
            
            scored_duplicates.append((score, para))
        
        # Sort by score (highest first) and return the best
        scored_duplicates.sort(key=lambda x: x[0], reverse=True)
        best_para = scored_duplicates[0][1]
        
        logger.debug(f"Chose duplicate with section_path='{best_para.section_path}' "
                    f"over {len(duplicates)-1} alternatives")
        
        return best_para
    
    def _merge_short_paragraphs(self, paragraphs: List[SegmentedParagraph], min_tokens: int = 100) -> List[SegmentedParagraph]:
        """
        Merge paragraphs with fewer than min_tokens with the previous paragraph.
        
        Args:
            paragraphs: List of segmented paragraphs
            min_tokens: Minimum token count threshold
            
        Returns:
            List with short paragraphs merged
        """
        if not paragraphs:
            return paragraphs
        
        merged_paragraphs = []
        
        for i, para in enumerate(paragraphs):
            if (para.tokens < min_tokens and 
                merged_paragraphs and  # There's a previous paragraph to merge with
                para.paragraph_type not in ['header', 'figure_caption', 'table']):  # Don't merge special types
                
                # Merge with the previous paragraph
                prev_para = merged_paragraphs[-1]
                
                # Check if they're on the same page or adjacent pages
                page_diff = abs(para.page - prev_para.page)
                if page_diff <= 1:  # Same page or adjacent pages
                    
                    # Check if bounding boxes are vertically adjacent (for better merging)
                    bbox_adjacent = self._are_bboxes_vertically_adjacent(prev_para.bbox, para.bbox)
                    
                    # Combine texts with appropriate spacing
                    if bbox_adjacent:
                        # If bounding boxes are adjacent, merge smoothly
                        combined_text = f"{prev_para.text.rstrip()} {para.text.lstrip()}"
                    else:
                        # If not adjacent, add line break for clarity
                        combined_text = f"{prev_para.text.rstrip()}\n{para.text.lstrip()}"
                    
                    # Update the previous paragraph
                    prev_para.text = combined_text
                    prev_para.tokens = self._estimate_token_count(combined_text)
                    
                    # Expand bounding box to include both paragraphs intelligently
                    if bbox_adjacent:
                        # For adjacent boxes, create a seamless combined box
                        prev_para.bbox['x1'] = min(prev_para.bbox['x1'], para.bbox['x1'])
                        prev_para.bbox['y1'] = min(prev_para.bbox['y1'], para.bbox['y1'])
                        prev_para.bbox['x2'] = max(prev_para.bbox['x2'], para.bbox['x2'])
                        prev_para.bbox['y2'] = max(prev_para.bbox['y2'], para.bbox['y2'])
                    else:
                        # For non-adjacent boxes, create an encompassing box
                        prev_para.bbox['x1'] = min(prev_para.bbox['x1'], para.bbox['x1'])
                        prev_para.bbox['y1'] = min(prev_para.bbox['y1'], para.bbox['y1'])
                        prev_para.bbox['x2'] = max(prev_para.bbox['x2'], para.bbox['x2'])
                        prev_para.bbox['y2'] = max(prev_para.bbox['y2'], para.bbox['y2'])
                    
                    # Update char span if both have it
                    if prev_para.char_span and para.char_span:
                        prev_para.char_span['end'] = para.char_span['end']
                    
                    # Prefer the more specific section path
                    if para.section_path and (not prev_para.section_path or 
                                            len(para.section_path) > len(prev_para.section_path)):
                        prev_para.section_path = para.section_path
                    
                    # Regenerate stable ID for the merged paragraph
                    prev_para.stable_id = self._generate_stable_id(
                        prev_para.doc_id, 
                        prev_para.page, 
                        prev_para.bbox, 
                        prev_para.text
                    )
                    
                    logger.debug(f"Merged short paragraph ({para.tokens} tokens) with previous paragraph (adjacent: {bbox_adjacent})")
                    continue  # Skip adding the current paragraph
            
            # Add paragraph as is (not merged)
            merged_paragraphs.append(para)
        
        # Re-assign paragraph indices
        for i, para in enumerate(merged_paragraphs):
            para.para_idx = i
        
        merged_count = len(paragraphs) - len(merged_paragraphs)
        if merged_count > 0:
            logger.info(f"Merged {merged_count} short paragraphs with previous ones")
        
        return merged_paragraphs

    def _are_bboxes_vertically_adjacent(self, bbox1: Dict[str, float], bbox2: Dict[str, float], tolerance: float = 10.0) -> bool:
        """
        Check if two bounding boxes are vertically adjacent (one below the other).
        
        Args:
            bbox1: First bounding box
            bbox2: Second bounding box  
            tolerance: Allowed gap between boxes to consider them adjacent
            
        Returns:
            True if boxes are vertically adjacent
        """
        # Check if they overlap horizontally (same column)
        horizontal_overlap = not (bbox1['x2'] < bbox2['x1'] or bbox2['x2'] < bbox1['x1'])
        
        if not horizontal_overlap:
            return False
        
        # Check vertical adjacency
        # Case 1: bbox1 is above bbox2
        gap1 = abs(bbox2['y1'] - bbox1['y2'])
        # Case 2: bbox2 is above bbox1  
        gap2 = abs(bbox1['y1'] - bbox2['y2'])
        
        # Consider adjacent if gap is within tolerance
        return min(gap1, gap2) <= tolerance