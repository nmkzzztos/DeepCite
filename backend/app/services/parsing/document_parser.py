"""
Multi-strategy PDF parsing service that supports multiple parsing approaches:
1. TOC-based parsing with smart section detection and missing section discovery
2. Standard PDF parsing as fallback
"""
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .pdf_content_extractor import PDFParser, ParsedDocument
from .structure_parser import TOCParser, TOCParseResult
from .paragraph_segmenter import TextSegmenter, SegmentedParagraph

logger = logging.getLogger(__name__)


class ParsingStrategy(Enum):
    """Available parsing strategies."""
    AUTO = "auto"           # Automatic strategy selection
    TOC = "toc"             # TOC-based parsing
    STANDARD = "standard"   # Standard PDF parsing


@dataclass
class GlobalParseResult:
    """Result of multi-strategy PDF parsing with multiple approach support."""
    strategy_used: ParsingStrategy
    document: ParsedDocument
    paragraphs: List[SegmentedParagraph]
    toc_result: Optional[TOCParseResult] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class GlobalPDFParser:
    """
    Multi-strategy PDF parser supporting multiple parsing approaches.
    
    This service acts as a coordinator between different parsing strategies:
    - TOC-based parsing for documents with table of contents and missing section detection
    - Standard PDF parsing as reliable fallback
    """
    
    def __init__(self):
        """
        Initialize the multi-strategy PDF parser.
        """
        self.pdf_parser = PDFParser()
        self.toc_parser = TOCParser()
        self.text_segmenter = TextSegmenter()
        
        # Strategy preferences and fallback chain
        self.strategy_fallback = {
            ParsingStrategy.AUTO: [ParsingStrategy.TOC, ParsingStrategy.STANDARD],
            ParsingStrategy.TOC: [ParsingStrategy.TOC, ParsingStrategy.STANDARD],
            ParsingStrategy.STANDARD: [ParsingStrategy.STANDARD]
        }
    
    def parse_document(
        self, 
        pdf_path: str, 
        strategy: ParsingStrategy = ParsingStrategy.AUTO,
        **options
    ) -> GlobalParseResult:
        """
        Parse a PDF document using the specified strategy.
        
        Args:
            pdf_path: Path to PDF file
            strategy: Parsing strategy to use
            **options: Additional parsing options
        
        Returns:
            GlobalParseResult with parsed content
        """
        return self._parse_with_fallback(pdf_path, None, strategy, **options)
    
    def parse_document_bytes(
        self, 
        pdf_bytes: bytes, 
        strategy: ParsingStrategy = ParsingStrategy.AUTO,
        **options
    ) -> GlobalParseResult:
        """
        Parse a PDF document from bytes using the specified strategy.
        
        Args:
            pdf_bytes: PDF content as bytes
            strategy: Parsing strategy to use
            **options: Additional parsing options
        
        Returns:
            GlobalParseResult with parsed content
        """
        return self._parse_with_fallback(None, pdf_bytes, strategy, **options)
    
    def _parse_with_fallback(
        self,
        pdf_path: Optional[str],
        pdf_bytes: Optional[bytes],
        strategy: ParsingStrategy,
        **options
    ) -> GlobalParseResult:
        """Parse with fallback strategy support."""
        strategies_to_try = self.strategy_fallback.get(strategy, [ParsingStrategy.STANDARD])
        warnings = []
        last_error = None
        
        for attempt_strategy in strategies_to_try:
            try:
                logger.info(f"Attempting to parse with strategy: {attempt_strategy.value}")
                
                if attempt_strategy == ParsingStrategy.TOC:
                    result = self._parse_with_toc(pdf_path, pdf_bytes, **options)
                elif attempt_strategy == ParsingStrategy.STANDARD:
                    result = self._parse_standard(pdf_path, pdf_bytes, **options)
                else:
                    continue
                
                result.warnings.extend(warnings)
                logger.info(f"Successfully parsed with strategy: {attempt_strategy.value}")
                return result
                
            except Exception as e:
                error_msg = f"Failed to parse with {attempt_strategy.value}: {str(e)}"
                logger.warning(error_msg)
                warnings.append(error_msg)
                last_error = e
                continue
        
        # If all strategies failed, raise the last error
        raise RuntimeError(f"All parsing strategies failed. Last error: {str(last_error)}")
    

    
    def _parse_with_toc(
        self,
        pdf_path: Optional[str],
        pdf_bytes: Optional[bytes],
        **options
    ) -> GlobalParseResult:
        """Parse using TOC strategy."""
        # Parse with TOC parser
        if pdf_path:
            toc_result = self.toc_parser.parse_document(pdf_path, **options)
            # Also get standard parsed document for compatibility
            parsed_doc = self.pdf_parser.parse_document(pdf_path)
        else:
            toc_result = self.toc_parser.parse_document_bytes(pdf_bytes, **options)
            parsed_doc = self.pdf_parser.parse_document_from_bytes(pdf_bytes)
        
        # Convert TOC sections to segmented paragraphs
        paragraphs = self._convert_toc_to_paragraphs(toc_result, parsed_doc.file_hash)
        
        warnings = []
        if toc_result.missing_sections_found > 0:
            warnings.append(f"Found {toc_result.missing_sections_found} missing academic sections")
        
        return GlobalParseResult(
            strategy_used=ParsingStrategy.TOC,
            document=parsed_doc,
            paragraphs=paragraphs,
            toc_result=toc_result,
            warnings=warnings
        )
    
    def _parse_standard(
        self,
        pdf_path: Optional[str],
        pdf_bytes: Optional[bytes],
        **options
    ) -> GlobalParseResult:
        """Parse using standard strategy."""
        if pdf_path:
            parsed_doc = self.pdf_parser.parse_document(pdf_path)
        else:
            parsed_doc = self.pdf_parser.parse_document_from_bytes(pdf_bytes)
        
        # Segment text without external structure
        paragraphs = self.text_segmenter.segment_document(
            parsed_doc,
            doc_id=parsed_doc.file_hash
        )
        
        return GlobalParseResult(
            strategy_used=ParsingStrategy.STANDARD,
            document=parsed_doc,
            paragraphs=paragraphs,
            warnings=[]
        )
    
    def _convert_toc_to_paragraphs(
        self,
        toc_result: TOCParseResult,
        doc_id: str
    ) -> List[SegmentedParagraph]:
        """Convert TOC sections to segmented paragraphs format."""
        from .paragraph_segmenter import SegmentedParagraph
        import hashlib

        paragraphs = []
        global_para_idx = 0

        def process_section(section, parent_path=""):
            nonlocal global_para_idx

            # Build section path - use only current section title without parent path
            current_path = section.title

            # Convert section paragraphs to SegmentedParagraph objects
            for para_text in section.paragraphs:
                if len(para_text.strip()) < 10:  # Skip very short paragraphs
                    continue

                # Generate stable ID for paragraph
                hash_input = f"{doc_id}:{section.start_page}:{global_para_idx}:{para_text[:100]}"
                stable_id = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

                # Estimate bbox (simplified)
                bbox = {
                    'x1': 50.0,
                    'y1': 100.0 + (global_para_idx * 20),
                    'x2': 500.0,
                    'y2': 120.0 + (global_para_idx * 20)
                }

                # Create segmented paragraph
                paragraph = SegmentedParagraph(
                    stable_id=stable_id,
                    doc_id=doc_id,
                    page=section.start_page,
                    para_idx=global_para_idx,
                    text=para_text.strip(),
                    bbox=bbox,
                    char_span=None,
                    section_path=current_path,
                    paragraph_type='paragraph',
                    tokens=max(1, len(para_text) // 4),  # Rough estimate
                    font_size=11.0,
                    is_bold=False,
                    is_italic=False
                )

                paragraphs.append(paragraph)
                global_para_idx += 1

            # Process children recursively - pass current path for context but don't use in section_path
            for child in section.children:
                process_section(child, current_path)

        # Process all top-level sections
        for section in toc_result.sections:
            process_section(section)
        
        # Merge short paragraphs (< 100 tokens) with previous ones
        merged_paragraphs = self._merge_short_toc_paragraphs(paragraphs)
        
        return merged_paragraphs

    def _merge_short_toc_paragraphs(self, paragraphs: List[SegmentedParagraph], min_tokens: int = 100) -> List[SegmentedParagraph]:
        """
        Merge TOC paragraphs with fewer than min_tokens with the previous paragraph.
        
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
                
                # Check if they're in the same section (same section_path)
                same_section = (para.section_path == prev_para.section_path)
                
                if same_section:
                    # Check if bounding boxes are vertically adjacent
                    bbox_adjacent = self._are_toc_bboxes_vertically_adjacent(prev_para.bbox, para.bbox)
                    
                    # Combine texts with appropriate spacing
                    if bbox_adjacent:
                        # If bounding boxes are adjacent, merge smoothly
                        combined_text = f"{prev_para.text.rstrip()} {para.text.lstrip()}"
                    else:
                        # If not adjacent, add line break for clarity
                        combined_text = f"{prev_para.text.rstrip()}\n{para.text.lstrip()}"
                    
                    # Update the previous paragraph
                    prev_para.text = combined_text
                    prev_para.tokens = max(1, len(combined_text) // 4)  # Rough estimate
                    
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
                    
                    # Regenerate stable ID for the merged paragraph
                    import hashlib
                    hash_input = f"{prev_para.doc_id}:{prev_para.page}:{prev_para.para_idx}:{prev_para.text[:100]}"
                    prev_para.stable_id = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                    
                    logger.debug(f"Merged short TOC paragraph ({para.tokens} tokens) with previous paragraph (adjacent: {bbox_adjacent})")
                    continue  # Skip adding the current paragraph
            
            # Add paragraph as is (not merged)
            merged_paragraphs.append(para)
        
        # Re-assign paragraph indices
        for i, para in enumerate(merged_paragraphs):
            para.para_idx = i
        
        merged_count = len(paragraphs) - len(merged_paragraphs)
        if merged_count > 0:
            logger.info(f"Merged {merged_count} short TOC paragraphs with previous ones")
        
        return merged_paragraphs

    def _are_toc_bboxes_vertically_adjacent(self, bbox1: Dict[str, float], bbox2: Dict[str, float], tolerance: float = 25.0) -> bool:
        """
        Check if two TOC bounding boxes are vertically adjacent.
        
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
    
    def get_available_strategies(self) -> Dict[str, bool]:
        """
        Get available parsing strategies and their status.
        
        Returns:
            Dictionary mapping strategy names to availability status
        """
        return {
            "standard": True,
            "toc": True,
            "auto": True
        }
    
    def recommend_strategy(self, pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> ParsingStrategy:
        """
        Recommend the best parsing strategy for a document.
        
        Args:
            pdf_path: Path to PDF file (optional)
            pdf_bytes: PDF content as bytes (optional)
        
        Returns:
            Recommended parsing strategy
        """
        # Quick analysis to recommend strategy
        try:
            # Try to get TOC to see if document has structure
            if pdf_path:
                import fitz
                doc = fitz.open(pdf_path)
            else:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            toc = doc.get_toc()
            doc.close()
            
            # If document has TOC, prefer TOC strategy
            if toc and len(toc) > 2:  # More than just title page entries
                return ParsingStrategy.TOC
            
            # Fallback to standard
            return ParsingStrategy.STANDARD
            
        except Exception:
            return ParsingStrategy.STANDARD
    
    def parse_with_multiple_strategies(
        self,
        pdf_path: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        strategies: List[ParsingStrategy] = None,
        **options
    ) -> Dict[ParsingStrategy, GlobalParseResult]:
        """
        Parse document with multiple strategies for comparison.
        
        Args:
            pdf_path: Path to PDF file (optional)
            pdf_bytes: PDF content as bytes (optional)
            strategies: List of strategies to try (defaults to all available)
            **options: Additional parsing options
        
        Returns:
            Dictionary mapping strategies to their parse results
        """
        if strategies is None:
            strategies = [
                ParsingStrategy.STANDARD,
                ParsingStrategy.TOC,
            ]
        
        results = {}
        
        for strategy in strategies:
            try:
                if pdf_path:
                    result = self.parse_document(pdf_path, strategy, **options)
                else:
                    result = self.parse_document_bytes(pdf_bytes, strategy, **options)
                results[strategy] = result
                logger.info(f"Successfully parsed with {strategy.value} strategy")
            except Exception as e:
                logger.warning(f"Failed to parse with {strategy.value} strategy: {e}")
                continue
        
        return results
