"""
Enhanced TOC-based PDF parsing service with smart section detection and citation analysis.
Based on the advanced algorithm from test.py with support for missing sections detection,
reference parsing, and citation linking.
"""
import fitz  # PyMuPDF
import hashlib
import re
import difflib
import statistics
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TOCEntry:
    """Table of Contents entry with enhanced metadata."""
    idx: int
    level: int
    title: str
    start_page: int  # 0-based
    end_page: int    # 0-based, inclusive (filled later)
    next_same_or_higher: Optional[int] = None  # index of the next record with level <=
    anchor: Optional[Tuple[float, float]] = None  # (y0, y1) of the heading on start_page
    children: List["TOCEntry"] = field(default_factory=list)


@dataclass
class ParsedReference:
    """Parsed bibliographic reference."""
    number: int
    raw_text: str
    authors: str = ""
    title: str = ""
    year: str = ""
    journal: str = ""
    links: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Citation:
    """Citation found in text."""
    type: str  # 'numbered' or 'author_year'
    text: str
    position: Tuple[int, int]
    reference_number: Optional[int] = None
    citation_content: Optional[str] = None
    reference: Optional[ParsedReference] = None


@dataclass
class EnhancedSection:
    """Enhanced section with TOC-based structure."""
    level: int
    title: str
    start_page: int
    end_page: int
    paragraphs: List[str]
    paragraphs_own: Optional[List[str]] = None  # Without children content
    references: Optional[List[ParsedReference]] = None
    citations: Optional[List[Citation]] = None
    children: List["EnhancedSection"] = field(default_factory=list)


@dataclass
class TOCParseResult:
    """Result of TOC-based parsing."""
    pdf_path: str
    page_count: int
    total_references: int
    sections: List[EnhancedSection]
    references: Optional[List[ParsedReference]] = None  # Global references list
    missing_sections_found: int = 0


class TOCParser:
    """
    Enhanced PDF parser using Table of Contents with smart section detection.
    
    Features:
    - TOC-based hierarchical section parsing
    - Automatic detection of missing academic sections (Abstract, References, etc.)
    - Reference parsing and citation analysis
    - Two-column layout detection and handling
    - Anchor-based precise section boundaries
    """
    
    def __init__(self):
        """Initialize the TOC parser with configuration."""
        self.min_chars = 10
        self.drop_captions = False
        
        # Regular expressions for text processing
        self._re_hyphen = re.compile(r"(\w)-\n(\w)")
        self._re_single_newline = re.compile(r"(?<!\n)\n(?!\n)")
        self._re_multispaces = re.compile(r"[ \t]{2,}")
        self._re_is_caption = re.compile(r"^(Figure|Fig\.|Table|Tab\.|Рис\.|Табл\.)\b", re.I)
        self._re_num_prefix = re.compile(r"^\s*\d+(?:[\.\u2024\u2027\u2219\u25CF·]\d+)*\s*[-–—\.\):]?\s*", re.U)
        
        # Link detection patterns
        self._re_arxiv_id = re.compile(r"(?:arxiv:|abs/)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
        self._re_doi = re.compile(r"(?:doi:|DOI:)?\s*10\.\d+/[^\s]+", re.I)
        self._re_url = re.compile(r"https?://[^\s<>\[\]()\"']+", re.I)
        self._re_email = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        
        # Academic section patterns
        self._re_academic_sections = re.compile(
            r"^\s*(Abstract|Introduction|Related\s+Work|Methodology|Method|Results|Discussion|Conclusion|References|Bibliography|Acknowledgments?|Appendix)\s*$", 
            re.I | re.M
        )
        
        # Reference parsing patterns
        self._re_reference_entry = re.compile(r"^\s*(\[?\d+\]?\.?|\(\d+\))\s*(.+)", re.M)
        self._re_author_year = re.compile(r"([A-Za-z\s,]+?)[\.,]\s*\((\d{4}[a-z]?)\)", re.M)
        self._re_numbered_ref = re.compile(r"\[(\d+)\]")
        self._re_author_year_citation = re.compile(r"\(([A-Za-z\s,]+?,\s*\d{4}[a-z]?)\)")
    
    def parse_document(self, pdf_path: str, **options) -> TOCParseResult:
        """
        Parse PDF document using TOC-based approach.
        
        Args:
            pdf_path: Path to PDF file
            **options: Parsing options (min_level, max_level, own_only, include_children_text, include_missing_sections)
        
        Returns:
            TOCParseResult with parsed structure
        """
        try:
            doc = fitz.open(pdf_path)
            result = self._extract_sections_from_doc(doc, pdf_path, **options)
            doc.close()
            return result
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {e}")
            raise
    
    def parse_document_bytes(self, pdf_bytes: bytes, **options) -> TOCParseResult:
        """
        Parse PDF document from bytes using TOC-based approach.
        
        Args:
            pdf_bytes: PDF content as bytes
            **options: Parsing options
        
        Returns:
            TOCParseResult with parsed structure
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            result = self._extract_sections_from_doc(doc, "bytes_document", **options)
            doc.close()
            return result
        except Exception as e:
            logger.error(f"Error parsing PDF from bytes: {e}")
            raise
    
    def _extract_sections_from_doc(
        self, 
        doc: fitz.Document, 
        pdf_path: str,
        min_level: Optional[int] = 1,
        max_level: Optional[int] = 2,  # Default to max level 2
        own_only: bool = False,
        include_children_text: bool = True,
        include_missing_sections: bool = True
    ) -> TOCParseResult:
        """Extract sections from PyMuPDF document."""
        
        # Get TOC entries
        entries = self._get_toc_entries(doc)
        
        # Add missing academic sections if requested
        missing_sections_count = 0
        if include_missing_sections:
            missing_sections = self._find_missing_academic_sections(doc, entries)
            if missing_sections:
                entries.extend(missing_sections)
                missing_sections_count = len(missing_sections)
                # Re-sort by page and level
                entries.sort(key=lambda e: (e.start_page, e.level))
                # Re-index
                for i, e in enumerate(entries):
                    e.idx = i
        
        if not entries:
            raise RuntimeError("No TOC (bookmarks/table of contents) or academic sections found in the PDF.")
        
        # Assign end pages and next references
        self._assign_end_and_next(entries, total_pages=doc.page_count)
        
        # Find heading anchors on pages
        self._annotate_anchors(doc, entries)
        
        # First pass: extract references from References section
        all_references = []
        for entry in entries:
            if self._norm_for_match(entry.title) in ["references", "bibliography"]:
                try:
                    ranges = [(entry.start_page, entry.end_page)]
                    page_cuts = self._compute_page_cuts_for_node(entry, entries)
                    _, references = self._extract_paragraphs_from_ranges(
                        doc, ranges, page_cuts=page_cuts, is_references_section=True
                    )
                    all_references.extend(references)
                    break  # Assume only one References section
                except Exception as e:
                    logger.warning(f"Error extracting references: {e}")
                    continue
        
        # Build tree structure
        roots = self._build_tree(entries)
        
        # Convert to enhanced sections
        tree = []
        for r in roots:
            section = self._node_to_enhanced_section(
                doc, r, entries, own_only, include_children_text, 
                min_level, max_level, all_references
            )
            if section is not None:
                tree.append(section)
        
        return TOCParseResult(
            pdf_path=pdf_path,
            page_count=doc.page_count,
            total_references=len(all_references),
            sections=tree,
            references=all_references if all_references else None,
            missing_sections_found=missing_sections_count
        )
    
    def _get_toc_entries(self, doc: fitz.Document) -> List[TOCEntry]:
        """Extract TOC entries from document, limiting to levels 1 and 2."""
        toc_raw = doc.get_toc(simple=True) or []   # [[lvl, title, page1], ...]
        entries: List[TOCEntry] = []
        for i, (lvl, title, page1) in enumerate(toc_raw):
            level = int(lvl)
            # Only include levels 1 and 2
            if level <= 2:
                p0 = max(0, int(page1) - 1)
                entries.append(TOCEntry(idx=len(entries), level=level, title=title.strip(), start_page=p0, end_page=-1))
        return entries
    
    def _assign_end_and_next(self, entries: List[TOCEntry], total_pages: int) -> None:
        """Determine end_page and link to the next record with level <=."""
        n = len(entries)
        for i, e in enumerate(entries):
            end = total_pages - 1
            nxt = None
            for j in range(i + 1, n):
                if entries[j].level <= e.level:
                    end = max(e.start_page, entries[j].start_page - 1)
                    nxt = j
                    break
            e.end_page = end
            e.next_same_or_higher = nxt
    
    def _build_tree(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """Build hierarchical tree from flat TOC entries."""
        roots: List[TOCEntry] = []
        stack: List[TOCEntry] = []
        for e in entries:
            while stack and stack[-1].level >= e.level:
                stack.pop()
            if stack:
                stack[-1].children.append(e)
            else:
                roots.append(e)
            stack.append(e)
        return roots
    
    def _normalize_block_text(self, raw: str) -> str:
        """Normalize text block content."""
        if not raw:
            return ""
        text = raw.replace("\r\n", "\n").replace("\r", "\n")
        text = self._re_hyphen.sub(r"\1\2", text)
        text = self._re_single_newline.sub(" ", text)
        text = self._re_multispaces.sub(" ", text)
        text = "\n".join(line.strip() for line in text.split("\n"))
        return text.strip()
    
    def _norm_for_match(self, s: str) -> str:
        """Normalize for comparison: lowercase, remove extra, collapse spaces."""
        s = s.lower()
        s = re.sub(r"[\s\-–—_:;,.()\[\]{}]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s
    
    def _title_variants(self, title: str) -> List[str]:
        """Title variants: with/without numbering."""
        t = title.strip()
        no_num = self._re_num_prefix.sub("", t)
        variants = {self._norm_for_match(t), self._norm_for_match(no_num)}
        return list(variants)
    
    def _block_fontsize(self, block: dict) -> float:
        """Max font size of the block by spans."""
        sizes = []
        for ln in block.get("lines", []):
            for sp in ln.get("spans", []):
                if isinstance(sp.get("size"), (int, float)):
                    sizes.append(float(sp["size"]))
        return max(sizes) if sizes else 0.0
    
    def _block_text(self, block: dict) -> str:
        """Collect block text."""
        parts = []
        for ln in block.get("lines", []):
            for sp in ln.get("spans", []):
                parts.append(sp.get("text", ""))
            parts.append("\n")
        return "".join(parts).strip()
    
    def _find_heading_anchor_on_page(self, page: fitz.Page, title: str) -> Optional[Tuple[float, float]]:
        """
        Returns (y0, y1) of the heading block on the page or None.
        We search for similarity of the text and consider font size / position on the page.
        Enhanced with multiple search strategies.
        """
        try:
            pd = page.get_text("dict")
        except Exception:
            return None

        if not pd or "blocks" not in pd:
            return None

        variants = self._title_variants(title)
        blocks = [b for b in pd["blocks"] if b.get("type") == 0 and "bbox" in b]
        if not blocks:
            return None

        page_h = page.rect.height
        scored = []
        
        # Strategy 1: Direct text similarity matching
        for b in blocks:
            txt = self._normalize_block_text(self._block_text(b))
            if not txt or len(txt) > 200:  # Skip very long blocks
                continue
            
            txtn = self._norm_for_match(txt)
            # similarity with any title variant
            sim = max(difflib.SequenceMatcher(None, txtn, v).ratio() for v in variants)
            
            # Enhanced scoring with multiple factors
            size = self._block_fontsize(b)
            y0, y1 = b["bbox"][1], b["bbox"][3]
            
            # Position bonus - headers are usually in top 50% of page
            pos_factor = 1.0 - (y0 / max(page_h, 1.0))
            top_bonus = max(0.0, pos_factor) * 0.15
            
            # Font size bonus - headers are usually larger
            avg_font = 11.0  # Estimated average font size
            size_bonus = max(0.0, (size - avg_font) / avg_font) * 0.2
            
            # Bold text bonus
            is_bold = self._is_block_bold(b)
            bold_bonus = 0.1 if is_bold else 0.0
            
            # Length penalty for very long text (headers are usually short)
            length_penalty = max(0.0, (len(txt) - 50) / 100) * 0.1
            
            score = sim + top_bonus + size_bonus + bold_bonus - length_penalty
            scored.append((score, sim, size, y0, y1, b, txt))

        # Strategy 2: Pattern-based matching for numbered sections
        for b in blocks:
            txt = self._normalize_block_text(self._block_text(b))
            if not txt:
                continue
                
            # Check for numbered section patterns that match title
            for variant in variants:
                # Extract number from variant if present
                num_match = re.match(r'^(\d+(?:\.\d+)*)', variant)
                if num_match:
                    section_num = num_match.group(1)
                    # Look for this number at start of block text
                    if txt.strip().startswith(section_num):
                        sim = 0.9  # High similarity for number match
                        size = self._block_fontsize(b)
                        y0, y1 = b["bbox"][1], b["bbox"][3]
                        score = sim + 0.2  # Bonus for number match
                        scored.append((score, sim, size, y0, y1, b, txt))
                        break

        # Strategy 3: Keyword-based matching for section headers
        title_keywords = self._extract_keywords(title)
        if title_keywords:
            for b in blocks:
                txt = self._normalize_block_text(self._block_text(b))
                if not txt or len(txt) > 150:
                    continue
                
                txt_keywords = self._extract_keywords(txt)
                if txt_keywords:
                    keyword_overlap = len(title_keywords.intersection(txt_keywords))
                    if keyword_overlap > 0:
                        sim = keyword_overlap / len(title_keywords.union(txt_keywords))
                        if sim >= 0.3:  # Reasonable keyword overlap
                            size = self._block_fontsize(b)
                            y0, y1 = b["bbox"][1], b["bbox"][3]
                            score = sim + 0.1  # Bonus for keyword match
                            scored.append((score, sim, size, y0, y1, b, txt))

        if not scored:
            return None

        # Sort by score and return best match
        scored.sort(key=lambda t: t[0], reverse=True)
        
        # Try different similarity thresholds
        for min_sim in [0.6, 0.4, 0.25, 0.15]:
            for score, sim, size, y0, y1, b, txt in scored:
                if sim >= min_sim:
                    logger.debug(f"Found anchor for '{title}' with similarity {sim:.2f}: '{txt[:50]}...'")
                    return (float(y0), float(y1))

        # Fallback: if no good match, try to find any potential header in top half of page
        potential_headers = []
        for score, sim, size, y0, y1, b, txt in scored:
            if y0 < page_h * 0.6 and size >= 10 and len(txt) < 100:  # Reasonable header characteristics
                potential_headers.append((score, sim, size, y0, y1, b, txt))
        
        if potential_headers:
            potential_headers.sort(key=lambda t: t[0], reverse=True)
            score, sim, size, y0, y1, b, txt = potential_headers[0]
            logger.debug(f"Fallback anchor for '{title}': '{txt[:50]}...' (sim={sim:.2f})")
            return (float(y0), float(y1))

        return None

    def _is_potential_section_header(self, text: str, block: dict) -> bool:
        """
        Determine if a text block is potentially a section header based on formatting and content.

        Args:
            text: Text content of the block
            block: Full block dictionary from PyMuPDF

        Returns:
            True if the text looks like a section header
        """
        if not text or len(text.strip()) > 200:
            return False

        text = text.strip()

        # Check for numbered sections (e.g., "1. Introduction", "2.1 Methods")
        if re.match(r'^\d+(?:\.\d+)*\.?\s+[A-Z]', text):
            return True

        # Check for lettered sections (e.g., "A. Methods", "B.1 Results")
        if re.match(r'^[A-Z](?:\.\d+)*\.?\s+[A-Z]', text):
            return True

        # Check for uppercase headers (all caps or title case)
        if text.isupper() and len(text) < 100:
            return True

        # Check for title case with reasonable length
        words = text.split()
        if len(words) <= 10 and len(text) < 120:  # Slightly increased limits
            capitalized_words = sum(1 for word in words if word and word[0].isupper())
            if capitalized_words >= len(words) * 0.6:  # 60% of words start with capital
                return True

        # Check font formatting - headers are often bold or larger
        font_size = self._block_fontsize(block)
        is_bold = self._is_block_bold(block)

        # Bold text is likely a header regardless of size
        if is_bold and len(text) < 150:
            return True

        # Large font size indicates header
        if font_size > 10:  # Lower threshold than before
            return True

        # Check position on page - headers are often at the top
        bbox = block.get("bbox", [0, 0, 0, 0])
        if len(bbox) >= 4:
            y_position = bbox[1]  # Top Y coordinate
            # If text is in top 30% of page, more likely to be header
            if y_position < 200:  # Rough estimate for top of page
                if font_size > 9 or is_bold:
                    return True

        # Check for common section keywords
        section_keywords = [
            'abstract', 'introduction', 'background', 'motivation', 'methodology', 'method',
            'approach', 'results', 'discussion', 'conclusion', 'conclusions', 'summary',
            'references', 'bibliography', 'acknowledgments', 'acknowledgements', 'appendix',
            'literature', 'review', 'analysis', 'evaluation', 'experiments', 'implementation',
            'materials', 'procedures', 'algorithms', 'models', 'framework', 'architecture',
            'performance', 'validation', 'testing', 'case study', 'examples', 'applications'
        ]

        text_lower = text.lower()
        if any(keyword in text_lower for keyword in section_keywords):
            return True

        # Check for section-like patterns
        if re.match(r'^\d+\s+[A-Z]', text):  # "1 Introduction"
            return True

        return False

    def _extract_keywords(self, text: str) -> Set[str]:
        """
        Extract meaningful keywords from text for matching.
        
        Args:
            text: Input text
            
        Returns:
            Set of normalized keywords
        """
        if not text:
            return set()
        
        # Remove numbers and common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        
        # Extract words, normalize, and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())  # Words with 3+ letters
        keywords = {word for word in words if word not in stop_words}
        
        return keywords

    def _get_section_variations(self, section: str) -> List[str]:
        """
        Get common variations of a section name.
        
        Args:
            section: Base section name
            
        Returns:
            List of common variations
        """
        variations = [section]
        section_lower = section.lower()
        
        # Common variations for different sections
        variation_map = {
            'abstract': ['summary', 'overview'],
            'introduction': ['intro', 'background', 'motivation'],
            'related work': ['literature review', 'prior work', 'background', 'state of the art'],
            'methodology': ['methods', 'approach', 'technique', 'framework'],
            'method': ['methods', 'methodology', 'approach'],
            'results': ['findings', 'outcomes', 'evaluation'],
            'discussion': ['analysis', 'interpretation'],
            'conclusion': ['conclusions', 'summary', 'final remarks'],
            'references': ['bibliography', 'citations', 'works cited'],
            'acknowledgments': ['acknowledgements', 'thanks'],
            'appendix': ['appendices', 'supplementary material']
        }
        
        # Add variations for this section
        if section_lower in variation_map:
            variations.extend(variation_map[section_lower])
        
        # Add plural/singular variations
        if section_lower.endswith('s'):
            variations.append(section_lower[:-1])  # Remove 's'
        else:
            variations.append(section_lower + 's')  # Add 's'
        
        return variations

    def _find_subsections(self, doc: fitz.Document, found_sections: Dict[str, Dict], existing_titles: Set[str]) -> List:
        """
        Find subsections within already found main sections.

        Args:
            doc: PyMuPDF document
            found_sections: Dictionary of found main sections
            existing_titles: Set of existing TOC titles

        Returns:
            List of tuples (section_name, info_dict) for found subsections
        """
        subsections = []

        # Common subsection patterns to look for (only level 2, not deeper)
        subsection_patterns = [
            r'^\d+\.\d+\.?\s+[A-Z]',  # "1.1 Subsection"
            r'^[A-Z]\.\d+\.?\s+[A-Z]',  # "A.1 Subsection"
        ]

        # Search through pages where main sections were found
        pages_to_search = set(info["page"] for info in found_sections.values())
        # Also search a few pages after each main section
        extended_pages = set()
        for page in pages_to_search:
            for offset in range(5):  # Search up to 5 pages after
                if page + offset < doc.page_count:
                    extended_pages.add(page + offset)

        for page_num in sorted(extended_pages):
            try:
                page = doc.load_page(page_num)
                blocks = page.get_text("dict").get("blocks", [])

                for block in blocks:
                    if block.get("type") != 0:  # Skip non-text blocks
                        continue

                    text = self._block_text(block)
                    if not text or len(text.strip()) > 150:  # Skip very long blocks
                        continue

                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) > 120:
                            continue

                        # Check if this matches subsection patterns
                        is_subsection = False
                        for pattern in subsection_patterns:
                            if re.match(pattern, line):
                                is_subsection = True
                                break

                        if is_subsection and self._is_potential_section_header(line, block):
                            normalized_line = self._norm_for_match(line)
                            if normalized_line not in existing_titles:
                                # Check if this subsection doesn't already exist
                                if line not in found_sections:
                                    font_size = self._block_fontsize(block)
                                    if font_size >= 8:
                                        bbox = block.get("bbox", [0, 0, 0, 0])
                                        anchor = (float(bbox[1]), float(bbox[3]))

                                        subsection_info = {
                                            "page": page_num,
                                            "title": line,
                                            "anchor": anchor,
                                            "font_size": font_size,
                                            "similarity": 0.95  # High confidence for numbered subsections
                                        }
                                        subsections.append((line, subsection_info))

            except Exception:
                continue

        logger.info(f"Found {len(subsections)} additional subsections")
        return subsections

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings using various metrics.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Normalize texts for comparison
        norm1 = self._norm_for_match(text1)
        norm2 = self._norm_for_match(text2)

        # Exact match gets highest score
        if norm1 == norm2:
            return 1.0

        # Use difflib for sequence similarity
        seq_similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()

        # Also check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return max(seq_similarity, 0.8)

        # Check word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            jaccard_similarity = len(intersection) / len(union) if union else 0.0

            # Return weighted combination
            return (seq_similarity * 0.6) + (jaccard_similarity * 0.4)

        return seq_similarity

    def _is_block_bold(self, block: dict) -> bool:
        """
        Check if a text block is bold based on font flags.

        Args:
            block: PyMuPDF block dictionary

        Returns:
            True if the block contains bold text
        """
        try:
            if "lines" not in block:
                return False

            for line in block["lines"]:
                for span in line.get("spans", []):
                    flags = span.get("flags", 0)
                    # Check if bold flag is set (bit 4 in PyMuPDF flags)
                    if flags & 16:  # 2^4 = 16
                        return True

            return False
        except Exception:
            return False

    def _annotate_anchors(self, doc: fitz.Document, entries: List[TOCEntry]) -> None:
        """Find the heading anchor (anchor) for each record on the start page."""
        for e in entries:
            try:
                page = doc.load_page(e.start_page)
            except Exception:
                continue
            anchor = self._find_heading_anchor_on_page(page, e.title)
            e.anchor = anchor
    
    def _find_missing_academic_sections(self, doc: fitz.Document, existing_entries: List[TOCEntry]) -> List[TOCEntry]:
        """Find academic sections that are not in TOC but present in the document."""
        existing_titles = {self._norm_for_match(e.title) for e in existing_entries}
        missing_sections = []

        # Extended list of academic sections to look for
        academic_sections = [
            # Main sections
            "Abstract", "Introduction", "Background", "Motivation",
            # Literature and related work
            "Related Work", "Literature Review", "State of the Art", "Prior Work",
            # Methodology sections
            "Methodology", "Method", "Approach", "Materials and Methods",
            "Experimental Setup", "Experiments", "Implementation", "System Design",
            # Results and evaluation
            "Results", "Evaluation", "Performance", "Analysis", "Findings",
            "Experimental Results", "Evaluation Results",
            # Discussion sections
            "Discussion", "Interpretation", "Implications",
            # Conclusion sections
            "Conclusion", "Conclusions", "Summary", "Future Work",
            # References and bibliography
            "References", "Bibliography", "Citations",
            # Additional sections
            "Acknowledgments", "Acknowledgements", "Appendix", "Appendices",
            "Supplementary Material", "Author Contributions", "Competing Interests",
            "Data Availability", "Code Availability", "Ethics Statement",
            # Common subsection patterns
            "Problem Statement", "Research Questions", "Objectives", "Scope",
            "Limitations", "Contributions", "Novelty", "Significance"
        ]

        found_sections = {}

        # Search through all pages for section headings (limit to first 20 pages for efficiency)
        search_pages = min(20, doc.page_count)
        for page_num in range(search_pages):
            try:
                page = doc.load_page(page_num)
                blocks = page.get_text("dict").get("blocks", [])

                for block in blocks:
                    if block.get("type") != 0:  # Skip non-text blocks
                        continue

                    text = self._block_text(block)
                    if not text or len(text.strip()) > 200:  # Skip very long blocks
                        continue

                    # Check if this looks like a section heading
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) > 150:  # Skip very long lines
                            continue

                        # Enhanced section detection with multiple strategies
                        potential_match = None
                        
                        # Strategy 1: Direct similarity matching
                        if self._is_potential_section_header(line, block):
                            for section in academic_sections:
                                similarity = self._calculate_similarity(line, section)
                                if similarity >= 0.5:  # More flexible threshold
                                    potential_match = (section, line, similarity, "direct")
                                    break
                        
                        # Strategy 2: Keyword-based matching
                        if not potential_match:
                            line_keywords = self._extract_keywords(line)
                            for section in academic_sections:
                                section_keywords = self._extract_keywords(section)
                                if line_keywords and section_keywords:
                                    overlap = len(line_keywords.intersection(section_keywords))
                                    if overlap > 0:
                                        similarity = overlap / len(section_keywords)
                                        if similarity >= 0.5:
                                            potential_match = (section, line, similarity, "keyword")
                                            break
                        
                        # Strategy 3: Pattern-based matching for common variations
                        if not potential_match:
                            line_lower = line.lower().strip()
                            for section in academic_sections:
                                section_lower = section.lower().strip()
                                
                                # Check for partial matches
                                if (section_lower in line_lower or line_lower in section_lower) and len(line) < 100:
                                    if self._is_potential_section_header(line, block):
                                        similarity = 0.8  # High confidence for partial matches
                                        potential_match = (section, line, similarity, "partial")
                                        break
                                
                                # Check for common variations
                                variations = self._get_section_variations(section)
                                for variation in variations:
                                    if variation.lower() == line_lower:
                                        similarity = 0.9  # Very high confidence for variations
                                        potential_match = (section, line, similarity, "variation")
                                        break
                                if potential_match:
                                    break
                        
                        # If we found a potential match, process it
                        if potential_match:
                            section, matched_line, similarity, match_type = potential_match
                            normalized_line = self._norm_for_match(matched_line)
                            
                            if normalized_line not in existing_titles:
                                # Check formatting to confirm it's a heading
                                font_size = self._block_fontsize(block)
                                is_bold = self._is_block_bold(block)
                                
                                # More flexible criteria based on match type
                                min_font_size = 7 if match_type in ["direct", "variation"] else 8
                                
                                if font_size >= min_font_size or is_bold:
                                    bbox = block.get("bbox", [0, 0, 0, 0])
                                    anchor = (float(bbox[1]), float(bbox[3]))

                                    # Use section name as key, but store original line as title
                                    section_key = f"{section}_{page_num}" if section in found_sections else section
                                    
                                    found_sections[section_key] = {
                                        "page": page_num,
                                        "title": matched_line,  # Keep original formatting
                                        "anchor": anchor,
                                        "font_size": font_size,
                                        "similarity": similarity,
                                        "match_type": match_type
                                    }
                                    logger.debug(f"Found section '{matched_line}' (type: {match_type}, sim: {similarity:.2f})")

                            # Also check for numbered sections (e.g., "1. Introduction", "2. Methods")
                            numbered_match = re.match(r'^(\d+(?:\.\d+)*)\.?\s*(.+)$', line)
                            if numbered_match and self._is_potential_section_header(line, block):
                                section_number = numbered_match.group(1)
                                section_title = numbered_match.group(2).strip()
                                full_title = f"{section_number} {section_title}"

                                # Check if this numbered section is academic
                                for section in academic_sections:
                                    if self._calculate_similarity(section_title, section) >= 0.6:
                                        normalized_full = self._norm_for_match(full_title)
                                        if normalized_full not in existing_titles:
                                            font_size = self._block_fontsize(block)
                                            if font_size >= 8:
                                                bbox = block.get("bbox", [0, 0, 0, 0])
                                                anchor = (float(bbox[1]), float(bbox[3]))

                                                if full_title not in found_sections:
                                                    found_sections[full_title] = {
                                                        "page": page_num,
                                                        "title": full_title,
                                                        "anchor": anchor,
                                                        "font_size": font_size,
                                                        "similarity": 0.9  # High confidence for numbered sections
                                                    }
            except Exception:
                continue
        
        # Search for subsections within found sections
        subsection_entries = self._find_subsections(doc, found_sections, existing_titles)

        # Combine main sections and subsections
        all_missing = list(found_sections.items()) + subsection_entries

        # Convert found sections to TOCEntry objects
        for section_name, info in all_missing:
            # Determine level based on section numbering
            level = 1
            if re.match(r'^\d+\.\d+', info["title"]):  # Subsection like "1.1"
                level = 2
            elif re.match(r'^\d+\.\d+\.\d+', info["title"]):  # Sub-subsection like "1.1.1"
                level = 3
            elif re.match(r'^[A-Z]\.\d+', info["title"]):  # Subsection like "A.1"
                level = 2

            # Only include levels 1 and 2 (skip level 3 and higher)
            if level <= 2:
                entry = TOCEntry(
                    idx=len(existing_entries) + len(missing_sections),
                    level=level,
                    title=info["title"],
                    start_page=info["page"],
                    end_page=info["page"],  # Will be updated later
                    anchor=info["anchor"]
                )
                missing_sections.append(entry)

        logger.info(f"Found {len(missing_sections)} missing academic sections (including subsections)")
        return missing_sections
    
    def _is_two_column_layout(self, page: fitz.Page) -> bool:
        """Detect if a page has a two-column layout."""
        try:
            blocks = page.get_text("dict").get("blocks", [])
            if len(blocks) < 4:
                return False
            
            # Get text blocks with their positions
            text_blocks = []
            for block in blocks:
                if block.get("type") == 0:  # text block
                    bbox = block.get("bbox")
                    if bbox:
                        text_blocks.append(bbox)
            
            if len(text_blocks) < 4:
                return False
            
            # Calculate page width and find blocks in left/right halves
            page_width = page.rect.width
            mid_x = page_width / 2
            
            left_blocks = [b for b in text_blocks if b[2] < mid_x + 50]  # x1 < mid + tolerance
            right_blocks = [b for b in text_blocks if b[0] > mid_x - 50]  # x0 > mid - tolerance
            
            # If we have significant blocks on both sides, it's likely two-column
            return len(left_blocks) >= 2 and len(right_blocks) >= 2
        except Exception:
            return False
    
    def _sort_blocks_two_column(self, blocks: List, page_width: float) -> List:
        """Sort blocks for two-column layout: left column top-to-bottom, then right column."""
        if not blocks:
            return blocks
        
        mid_x = page_width / 2
        left_blocks = []
        right_blocks = []
        
        for block in blocks:
            if isinstance(block, (list, tuple)) and len(block) >= 5:
                x0, y0, x1, y1 = float(block[0]), float(block[1]), float(block[2]), float(block[3])
                center_x = (x0 + x1) / 2
                
                if center_x < mid_x:
                    left_blocks.append(block)
                else:
                    right_blocks.append(block)
            else:
                # Fallback for other block types
                left_blocks.append(block)
        
        # Sort each column by y-coordinate
        left_blocks.sort(key=lambda b: float(b[1]) if isinstance(b, (list, tuple)) and len(b) >= 2 else 0)
        right_blocks.sort(key=lambda b: float(b[1]) if isinstance(b, (list, tuple)) and len(b) >= 2 else 0)
        
        return left_blocks + right_blocks
    
    def _compute_page_cuts_for_node(self, node: TOCEntry, entries: List[TOCEntry]) -> Dict[int, Tuple[Optional[float], Optional[float]]]:
        """
        Returns a dictionary of cuts for the section pages:
        page_no -> (y_min, y_max), where
            - y_min: take only blocks BELOW this coordinate (first page)
            - y_max: take only blocks ABOVE this coordinate (last page when the next section starts on it)
        Enhanced with fallback strategies when anchors are missing.
        """
        cuts: Dict[int, Tuple[Optional[float], Optional[float]]] = {}
        eps = 5.0  # Increased gap for better separation

        # Lower boundary on the first page — after the heading of the current section
        if node.anchor is not None:
            y0, y1 = node.anchor
            cuts[node.start_page] = (y1 + eps, None)
        else:
            # Fallback: use estimated position based on page structure
            estimated_y = self._estimate_section_start_position(node, entries)
            if estimated_y is not None:
                cuts[node.start_page] = (estimated_y, None)
                logger.debug(f"Using estimated position {estimated_y} for section '{node.title}'")

        # Upper boundary on the last page — before the heading of the next section, if it starts here
        if node.next_same_or_higher is not None:
            nxt = entries[node.next_same_or_higher]
            if nxt.start_page == node.end_page:
                if nxt.anchor is not None:
                    y0_next, _ = nxt.anchor
                    prev = cuts.get(node.end_page, (None, None))
                    cuts[node.end_page] = (prev[0], y0_next - eps)
                else:
                    # Fallback: estimate next section position
                    estimated_y_next = self._estimate_section_start_position(nxt, entries)
                    if estimated_y_next is not None:
                        prev = cuts.get(node.end_page, (None, None))
                        cuts[node.end_page] = (prev[0], estimated_y_next - eps)

        # Add intermediate page boundaries for multi-page sections
        if node.end_page > node.start_page:
            for page_num in range(node.start_page + 1, node.end_page):
                # Check if any subsections start on this page
                subsection_y = self._find_subsection_on_page(page_num, node, entries)
                if subsection_y is not None:
                    cuts[page_num] = (subsection_y + eps, None)

        return cuts

    def _estimate_section_start_position(self, node: TOCEntry, entries: List[TOCEntry]) -> Optional[float]:
        """
        Estimate the Y position where a section starts on a page when anchor is not found.
        
        Args:
            node: TOC entry for the section
            entries: All TOC entries for context
            
        Returns:
            Estimated Y coordinate or None
        """
        # Strategy 1: Use average position of other sections with similar level
        similar_level_positions = []
        for entry in entries:
            if entry.level == node.level and entry.anchor is not None:
                y0, y1 = entry.anchor
                similar_level_positions.append(y0)
        
        if similar_level_positions:
            avg_position = statistics.median(similar_level_positions)
            return avg_position
        
        # Strategy 2: Use hierarchical positioning based on level
        base_positions = {
            1: 100.0,  # Main sections start higher
            2: 150.0,  # Subsections start lower
            3: 200.0,  # Sub-subsections even lower
        }
        
        estimated_y = base_positions.get(node.level, 120.0)
        
        # Adjust based on page content density
        return estimated_y

    def _find_subsection_on_page(self, page_num: int, parent_node: TOCEntry, entries: List[TOCEntry]) -> Optional[float]:
        """
        Find if any subsection starts on the given page within the parent section.
        
        Args:
            page_num: Page number to check
            parent_node: Parent section node
            entries: All TOC entries
            
        Returns:
            Y coordinate of subsection start or None
        """
        for entry in entries:
            # Check if this entry is a child of parent_node and starts on this page
            if (entry.level > parent_node.level and 
                entry.start_page == page_num and
                entry.idx > parent_node.idx and
                (parent_node.next_same_or_higher is None or entry.idx < parent_node.next_same_or_higher)):
                
                if entry.anchor is not None:
                    y0, y1 = entry.anchor
                    return y0
                else:
                    # Estimate position for subsection
                    return self._estimate_section_start_position(entry, entries)
        
        return None
    
    def _subtract_intervals(self, parent: Tuple[int, int], children: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Subtract children intervals from parent interval."""
        (a, b) = parent
        if a > b:
            return []
        segs = []
        for (c, d) in children:
            c = max(c, a); d = min(d, b)
            if c <= d:
                segs.append((c, d))
        if not segs:
            return [(a, b)]
        segs.sort()
        merged = [segs[0]]
        for c, d in segs[1:]:
            m0, m1 = merged[-1]
            if c <= m1 + 1:
                merged[-1] = (m0, max(m1, d))
            else:
                merged.append((c, d))
        cur = a
        out = []
        for c, d in merged:
            if cur < c:
                out.append((cur, c - 1))
            cur = d + 1
        if cur <= b:
            out.append((cur, b))
        return out
    
    def _flatten_children_intervals(self, node: TOCEntry) -> List[Tuple[int, int]]:
        """Get all children page intervals recursively."""
        acc: List[Tuple[int, int]] = []
        for ch in node.children:
            acc.append((ch.start_page, ch.end_page))
            acc.extend(self._flatten_children_intervals(ch))
        return acc
    
    def _extract_links_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract various types of links from text."""
        links = []
        
        # Extract arXiv IDs and convert to full URLs
        for match in self._re_arxiv_id.finditer(text):
            arxiv_id = match.group(1)
            start, end = match.span()
            original = text[start:end]
            url = f"https://arxiv.org/abs/{arxiv_id}"
            links.append({
                "type": "arxiv",
                "original": original,
                "url": url,
                "title": f"arXiv:{arxiv_id}"
            })
        
        # Extract DOIs
        for match in self._re_doi.finditer(text):
            doi = match.group(0).strip()
            start, end = match.span()
            # Clean up DOI
            clean_doi = doi.replace("doi:", "").replace("DOI:", "").strip()
            if not clean_doi.startswith("10."):
                continue
            url = f"https://doi.org/{clean_doi}"
            links.append({
                "type": "doi",
                "original": doi,
                "url": url,
                "title": clean_doi
            })
        
        # Extract regular URLs
        for match in self._re_url.finditer(text):
            url = match.group(0)
            # Skip if already processed as arXiv or DOI
            if any(link["url"] == url for link in links):
                continue
            links.append({
                "type": "url",
                "original": url,
                "url": url,
                "title": url
            })
        
        # Extract email addresses
        for match in self._re_email.finditer(text):
            email = match.group(0)
            links.append({
                "type": "email",
                "original": email,
                "url": f"mailto:{email}",
                "title": email
            })
        
        return links
    
    def _parse_reference_entry(self, text: str, ref_number: int) -> ParsedReference:
        """Parse a single reference entry and extract metadata."""
        reference = ParsedReference(
            number=ref_number,
            raw_text=text.strip()
        )
        
        # Extract links from the reference
        ref_links = self._extract_links_from_text(text)
        reference.links = ref_links
        
        # Try to extract author and year using common patterns
        author_year_match = self._re_author_year.search(text)
        if author_year_match:
            reference.authors = author_year_match.group(1).strip()
            reference.year = author_year_match.group(2).strip()
        
        # Try to extract title (usually in quotes or after authors)
        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            # Remove reference number from the beginning
            clean_line = self._re_reference_entry.sub(r'\2', first_line)
            if clean_line:
                # Try to split by common patterns to find title
                parts = re.split(r'[.]\s*["]([^"]+)["]', clean_line)
                if len(parts) > 1:
                    reference.title = parts[1].strip()
        
        return reference
    
    def _extract_references_from_section(self, text: str) -> List[ParsedReference]:
        """Extract and parse numbered references from References section."""
        references = []
        current_ref = ""
        current_number = 0
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new reference
            ref_match = self._re_reference_entry.match(line)
            if ref_match:
                # Save previous reference if exists
                if current_ref and current_number > 0:
                    ref_data = self._parse_reference_entry(current_ref, current_number)
                    references.append(ref_data)
                
                # Start new reference
                ref_number_text = ref_match.group(1)
                # Extract number from various formats: [1], 1., (1), etc.
                number_match = re.search(r'\d+', ref_number_text)
                if number_match:
                    current_number = int(number_match.group())
                else:
                    current_number = len(references) + 1
                
                current_ref = ref_match.group(2)
            else:
                # Continue current reference
                if current_ref:
                    current_ref += " " + line
        
        # Don't forget the last reference
        if current_ref and current_number > 0:
            ref_data = self._parse_reference_entry(current_ref, current_number)
            references.append(ref_data)
        
        # Sort references by number
        references.sort(key=lambda x: x.number)
        
        return references
    
    def _find_citations_in_text(self, text: str, references: List[ParsedReference]) -> List[Citation]:
        """Find citations in text and link them to references."""
        citations = []
        
        # Find numbered citations like [1], [2-4], [1,3,5]
        for match in self._re_numbered_ref.finditer(text):
            ref_num = int(match.group(1))
            start, end = match.span()
            
            # Find corresponding reference
            ref_data = None
            for ref in references:
                if ref.number == ref_num:
                    ref_data = ref
                    break
            
            citation = Citation(
                type="numbered",
                text=match.group(0),
                position=(start, end),
                reference_number=ref_num,
                reference=ref_data
            )
            citations.append(citation)
        
        # Find author-year citations like (Smith et al., 2020)
        for match in self._re_author_year_citation.finditer(text):
            citation_text = match.group(1)
            start, end = match.span()
            
            # Try to match with references by author and year
            ref_data = None
            for ref in references:
                if ref.authors and ref.year:
                    # Simple matching - could be improved
                    if ref.year in citation_text:
                        # Check if author names match (simplified)
                        author_parts = ref.authors.lower().split()
                        citation_lower = citation_text.lower()
                        if any(part in citation_lower for part in author_parts if len(part) > 2):
                            ref_data = ref
                            break
            
            citation = Citation(
                type="author_year",
                text=match.group(0),
                position=(start, end),
                citation_content=citation_text,
                reference=ref_data
            )
            citations.append(citation)
        
        return citations
    
    def _extract_paragraphs_from_ranges(
        self,
        doc: fitz.Document,
        ranges: List[Tuple[int, int]],
        page_cuts: Optional[Dict[int, Tuple[Optional[float], Optional[float]]]] = None,
        min_chars: int = 10,
        drop_captions: bool = False,
        is_references_section: bool = False
    ) -> Tuple[List[str], List[ParsedReference]]:
        """
        Returns a tuple of (paragraphs, references) by blocks, with cuts by y.
        If is_references_section=True, parses references instead of returning generic links.
        """
        paragraphs: List[str] = []
        references: List[ParsedReference] = []
        
        for (a, b) in ranges:
            for pno in range(a, b + 1):
                page = doc.load_page(pno)
                blocks = page.get_text("blocks") or []
                
                # Fallback: if there are no blocks — take the whole text and divide by empty lines
                if not blocks:
                    raw = page.get_text("text")
                    t = raw.replace("\r\n", "\n").replace("\r", "\n")
                    t = self._re_hyphen.sub(r"\1\2", t)
                    t = self._re_single_newline.sub(" ", t)
                    parts = [s.strip() for s in re.split(r"\n{2,}", t) if s.strip()]
                    paragraphs.extend(parts)
                    continue

                # Check if this is a two-column layout
                is_two_col = self._is_two_column_layout(page)
                
                # Filter valid text blocks
                valid_blocks = [b for b in blocks if isinstance(b, (list, tuple)) and len(b) >= 5 and isinstance(b[4], str)]
                
                # Sort blocks appropriately
                if is_two_col:
                    blocks_sorted = self._sort_blocks_two_column(valid_blocks, page.rect.width)
                else:
                    blocks_sorted = sorted(valid_blocks, key=lambda t: (round(t[1], 2), round(t[0], 2)))

                y_min, y_max = (None, None)
                if page_cuts and pno in page_cuts:
                    y_min, y_max = page_cuts[pno]

                for b in blocks_sorted:
                    x0, y0, x1, y1, txt = float(b[0]), float(b[1]), float(b[2]), float(b[3]), b[4]
                    # cuts by coordinates
                    if y_min is not None and y1 <= y_min:
                        continue
                    if y_max is not None and y0 >= y_max:
                        continue
                    text = self._normalize_block_text(txt)
                    if not text:
                        continue
                    if drop_captions and self._re_is_caption.match(text):
                        continue
                    if len(text) < min_chars:
                        continue
                    paragraphs.append(text)

        # Soft merging of «hanging» strings
        merged: List[str] = []
        terminals = ".!?:;…»)]»›"
        for para in paragraphs:
            if merged and not merged[-1].rstrip().endswith(tuple(terminals)):
                merged[-1] = (merged[-1] + " " + para).strip()
            else:
                merged.append(para)
        
        # If this is a references section, parse references instead of returning paragraphs
        if is_references_section and merged:
            full_text = "\n".join(merged)
            references = self._extract_references_from_section(full_text)
            return merged, references
        
        return merged, references
    
    def _node_to_enhanced_section(
        self,
        doc: fitz.Document,
        node: TOCEntry,
        entries_linear: List[TOCEntry],
        own_only: bool,
        include_children_text: bool,
        min_level: Optional[int],
        max_level: Optional[int],
        all_references: List[ParsedReference] = None
    ) -> Optional[EnhancedSection]:
        """Convert TOC node to enhanced section."""
        in_range = (min_level is None or node.level >= min_level) and (max_level is None or node.level <= max_level)

        full_range = [(node.start_page, node.end_page)]
        child_intervals = self._flatten_children_intervals(node)
        own_ranges = self._subtract_intervals((node.start_page, node.end_page), child_intervals)
        page_cuts = self._compute_page_cuts_for_node(node, entries_linear)

        section = None
        if in_range:
            ranges = full_range if include_children_text else own_ranges
            
            # Check if this is a References section
            is_references = self._norm_for_match(node.title) in ["references", "bibliography"]
            
            paragraphs, extracted_references = self._extract_paragraphs_from_ranges(
                doc, ranges, page_cuts=page_cuts, is_references_section=is_references
            )

            section = EnhancedSection(
                level=node.level,
                title=node.title,
                start_page=node.start_page + 1,  # Convert to 1-based
                end_page=node.end_page + 1,      # Convert to 1-based
                paragraphs=paragraphs,
            )

            # Handle references vs citations
            if is_references and extracted_references:
                section.references = extracted_references
            elif all_references and paragraphs:
                # Find citations in paragraphs
                all_text = "\n".join(paragraphs)
                citations = self._find_citations_in_text(all_text, all_references)
                if citations:
                    section.citations = citations

            if own_only:
                paragraphs_own, extracted_references_own = self._extract_paragraphs_from_ranges(
                    doc, own_ranges, page_cuts=page_cuts, is_references_section=is_references
                )
                section.paragraphs_own = paragraphs_own

        children_out = []
        for ch in node.children:
            ch_section = self._node_to_enhanced_section(
                doc, ch, entries_linear, own_only, include_children_text, 
                min_level, max_level, all_references
            )
            if ch_section is not None:
                children_out.append(ch_section)

        if section is None:
            if children_out:
                # Create a container section for children
                return EnhancedSection(
                    level=node.level,
                    title=node.title,
                    start_page=node.start_page + 1,
                    end_page=node.end_page + 1,
                    paragraphs=[],
                    children=children_out
                )
            return None

        if children_out:
            section.children = children_out
        return section
