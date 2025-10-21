#!/usr/bin/env python3
"""
Script to add arXiv papers to papers.json

This script fetches paper metadata from arXiv and adds it to the papers.json file
used by the DeepCite documentation site.

Usage:
    python add_paper.py <arxiv_id_or_url> [category] [citations]

Examples:
    # Interactive mode (will prompt for category and citations)
    python add_paper.py 2312.10997

    # Non-interactive mode with all parameters
    python add_paper.py 2312.10997 "RAG (Retrieval Augmented Generation)" 3343

    # Works with URLs too
    python add_paper.py https://arxiv.org/abs/2312.10997

Arguments:
    arxiv_id_or_url: arXiv paper ID (e.g., 2312.10997) or full URL
    category: Optional category string (will prompt if not provided)
    citations: Optional citation count (will prompt if not provided)
"""

import sys
import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
import httpx

# Handle Unicode encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class ArxivAuthor:
    def __init__(self, name: str, affiliation: Optional[str] = None):
        self.name = name
        self.affiliation = affiliation


class ArxivPaper:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.title = kwargs.get('title', '')
        self.summary = kwargs.get('summary', '')
        self.authors = kwargs.get('authors', [])
        self.published = kwargs.get('published', '')
        self.updated = kwargs.get('updated', '')
        self.categories = kwargs.get('categories', [])
        self.primaryCategory = kwargs.get('primaryCategory', '')
        self.pdfUrl = kwargs.get('pdfUrl', '')
        self.abstractUrl = kwargs.get('abstractUrl', '')
        self.doi = kwargs.get('doi')
        self.journalRef = kwargs.get('journalRef')
        self.comment = kwargs.get('comment')


class ArxivApiService:
    """Simplified ArxivApiService for standalone use"""

    def __init__(self):
        self.base_url = 'https://export.arxiv.org/api/query'

    async def searchPapers(self, params: Dict[str, Any]) -> List[ArxivPaper]:
        """Search arXiv papers by various criteria"""
        search_params = {}

        if 'query' in params:
            search_params['search_query'] = params['query']

        if 'idList' in params and params['idList']:
            search_params['id_list'] = ','.join(params['idList'])

        if 'start' in params:
            search_params['start'] = str(params['start'])

        if 'maxResults' in params:
            search_params['max_results'] = str(params['maxResults'])

        if 'sortBy' in params:
            search_params['sortBy'] = params['sortBy']

        if 'sortOrder' in params:
            search_params['sortOrder'] = params['sortOrder']

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params=search_params,
                    headers={'Accept': 'application/atom+xml'}
                )

                if response.status_code != 200:
                    print(f"arXiv API error: {response.status_code}")
                    return []

                return self._parse_arxiv_response(response.text)

        except Exception as e:
            print(f"Error fetching from arXiv: {e}")
            return []

    def _parse_arxiv_response(self, xml_data: str) -> List[ArxivPaper]:
        """Parse arXiv XML response to structured data"""
        try:
            root = ET.fromstring(xml_data)
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')

            papers = []
            for entry in entries:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)

            return papers

        except Exception as e:
            print(f"Error parsing arXiv response: {e}")
            return []

    def _parse_entry(self, entry) -> Optional[ArxivPaper]:
        """Parse individual arXiv entry"""
        try:
            # Extract basic fields
            id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
            title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
            summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
            published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
            updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')

            if id_elem is None or title_elem is None:
                return None

            if not id_elem.text or not title_elem.text:
                return None

            # Extract ID from URL
            id_url = id_elem.text or ''
            paper_id = id_url.split('/')[-1] if '/' in id_url else id_url

            title = (title_elem.text or '').strip()
            summary = (summary_elem.text or '').strip()
            published = published_elem.text or '' if published_elem else ''
            updated = updated_elem.text or '' if updated_elem else ''

            # Parse authors
            authors = []
            author_elements = entry.findall('{http://www.w3.org/2005/Atom}author')
            for author_elem in author_elements:
                name_elem = author_elem.find('{http://www.w3.org/2005/Atom}name')
                if name_elem is not None and name_elem.text:
                    name = name_elem.text.strip()
                    # Try to get affiliation
                    affiliation = None
                    affiliation_elem = author_elem.find('{http://arxiv.org/schemas/atom}affiliation')
                    if affiliation_elem is not None:
                        affiliation = affiliation_elem.text.strip()
                    authors.append(ArxivAuthor(name, affiliation))

            # Parse categories
            categories = []
            primary_category = ''
            category_elements = entry.findall('{http://www.w3.org/2005/Atom}category')
            for i, cat_elem in enumerate(category_elements):
                term = cat_elem.get('term', '')
                if term:
                    categories.append(term)
                    if i == 0:  # First category is primary
                        primary_category = term

            # Parse links
            pdf_url = ''
            abstract_url = ''
            link_elements = entry.findall('{http://www.w3.org/2005/Atom}link')
            for link_elem in link_elements:
                href = link_elem.get('href', '')
                rel = link_elem.get('rel', '')
                type_attr = link_elem.get('type', '')
                title_attr = link_elem.get('title', '')

                if type_attr == 'application/pdf' or title_attr == 'pdf':
                    pdf_url = href
                elif 'abs' in href:
                    abstract_url = href

            # Optional fields
            doi = None
            journal_ref = None
            comment = None

            doi_elem = entry.find('{http://arxiv.org/schemas/atom}doi')
            if doi_elem is not None:
                doi = doi_elem.text.strip()

            journal_elem = entry.find('{http://arxiv.org/schemas/atom}journal_ref')
            if journal_elem is not None:
                journal_ref = journal_elem.text.strip()

            comment_elem = entry.find('{http://arxiv.org/schemas/atom}comment')
            if comment_elem is not None:
                comment = comment_elem.text.strip()

            return ArxivPaper(
                id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                published=published,
                updated=updated,
                categories=categories,
                primaryCategory=primary_category,
                pdfUrl=pdf_url,
                abstractUrl=abstract_url,
                doi=doi,
                journalRef=journal_ref,
                comment=comment
            )

        except Exception as e:
            print(f"Error parsing arXiv entry: {e}")
            return None


def extract_arxiv_id(input_str: str) -> str:
    """Extract arXiv ID from URL or return as-is if it's already an ID"""
    # Handle URLs like https://arxiv.org/abs/2312.10997
    arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+)', input_str)
    if arxiv_match:
        return arxiv_match.group(1)

    # Handle direct ID input
    if re.match(r'^[0-9]+\.[0-9]+$', input_str):
        return input_str

    # Handle URLs with v1, v2, etc.
    arxiv_match_v = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]+\.[0-9]+)v\d+', input_str)
    if arxiv_match_v:
        return arxiv_match_v.group(1)

    raise ValueError(f"Could not extract valid arXiv ID from: {input_str}")


def create_paper_id(title: str) -> str:
    """Create URL-friendly ID from paper title"""
    # Convert to lowercase, replace spaces and special chars with hyphens
    id_str = title.lower()
    id_str = re.sub(r'[^\w\s-]', '', id_str)  # Remove special characters except spaces and hyphens
    id_str = re.sub(r'[\s_-]+', '-', id_str)  # Replace spaces, underscores, multiple hyphens with single hyphen
    id_str = id_str.strip('-')  # Remove leading/trailing hyphens
    return id_str


def format_authors(authors) -> str:
    """Format author list for JSON"""
    if isinstance(authors, list):
        # Handle ArxivAuthor objects
        author_names = []
        for author in authors:
            if hasattr(author, 'name'):
                author_names.append(author.name)
            else:
                author_names.append(str(author))
        return ', '.join(author_names)
    return str(authors)


def extract_year(date_str: str) -> int:
    """Extract year from ISO date string"""
    try:
        # Handle ISO format: 2023-12-15T10:30:00Z
        if 'T' in date_str:
            date_part = date_str.split('T')[0]
            return int(date_part.split('-')[0])
        # Handle other formats
        return int(date_str[:4])
    except (ValueError, IndexError):
        return datetime.now().year


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python add_paper.py <arxiv_id_or_url> [category] [citations]")
        print("Examples:")
        print("  python add_paper.py 2312.10997")
        print("  python add_paper.py https://arxiv.org/abs/2312.10997")
        print("  python add_paper.py 2312.10997 'RAG (Retrieval Augmented Generation)' 3343")
        sys.exit(1)

    input_str = sys.argv[1]
    category_arg = sys.argv[2] if len(sys.argv) >= 3 else None
    citations_arg = sys.argv[3] if len(sys.argv) >= 4 else None

    try:
        arxiv_id = extract_arxiv_id(input_str)
        print(f"Fetching paper: {arxiv_id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Initialize the ArxivApiService
    service = ArxivApiService()

    # Fetch paper data (using synchronous approach for simplicity)
    import asyncio

    async def fetch_paper():
        papers = await service.searchPapers({'idList': [arxiv_id]})
        return papers[0] if papers else None

    # Run the async function
    paper = asyncio.run(fetch_paper())

    if not paper:
        print(f"Error: Could not fetch paper with ID {arxiv_id}")
        sys.exit(1)

    # Create the paper entry
    paper_id = create_paper_id(paper.title)
    authors_str = format_authors(paper.authors)
    year = extract_year(paper.published or paper.updated)

    paper_entry = {
        "id": paper_id,
        "title": paper.title,
        "authors": authors_str,
        "year": year,
        "abstract": paper.summary,
        "category": "",  # Will be filled manually
        "url": f"https://arxiv.org/abs/{paper.id}",
        "arxiv": paper.id,
        "pdf": paper.pdfUrl or f"https://arxiv.org/pdf/{paper.id}.pdf",
        "citations": 0  # Will be filled manually
    }

    # Display the fetched information
    print("\n" + "="*80)
    print("FETCHED PAPER INFORMATION:")
    print("="*80)
    print(f"Title: {paper.title}")
    print(f"Authors: {authors_str}")
    print(f"Year: {year}")
    print(f"ArXiv ID: {paper.id}")
    print(f"Abstract (first 200 chars): {paper.summary[:200]}...")
    print("="*80)

    # Get category
    if category_arg:
        category = category_arg
        print(f"Category (from args): {category}")
    else:
        try:
            category = input("Category: ").strip()
            if not category:
                print("Warning: Category is empty. You can edit papers.json later to add it.")
        except EOFError:
            print("Warning: No category provided. You can edit papers.json later to add it.")
            category = ""

    # Get citations
    if citations_arg:
        try:
            citations = int(citations_arg)
            print(f"Citations (from args): {citations}")
        except ValueError:
            print(f"Warning: '{citations_arg}' is not a valid number. Setting citations to 0.")
            citations = 0
    else:
        try:
            citations_str = input("Citations (number): ").strip()
            citations = 0
            if citations_str:
                try:
                    citations = int(citations_str)
                except ValueError:
                    print(f"Warning: '{citations_str}' is not a valid number. Setting citations to 0.")
            else:
                print("Warning: Citations not provided. Setting to 0. You can edit papers.json later.")
        except EOFError:
            print("Warning: No citations provided. Setting to 0. You can edit papers.json later.")
            citations = 0

    # Update the entry
    paper_entry["category"] = category
    paper_entry["citations"] = citations

    # Load existing papers.json
    papers_file = Path(__file__).parent / "src" / "pages" / "papers.json"

    try:
        with open(papers_file, 'r', encoding='utf-8') as f:
            papers_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {papers_file} not found!")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {papers_file} contains invalid JSON!")
        sys.exit(1)

    # Check if paper already exists
    existing_ids = [p.get('id') for p in papers_data]
    if paper_id in existing_ids:
        print(f"Warning: Paper with ID '{paper_id}' already exists in papers.json")
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Aborted.")
            sys.exit(0)
        else:
            # Remove existing entry
            papers_data = [p for p in papers_data if p.get('id') != paper_id]

    # Add new paper to the beginning of the list
    papers_data.insert(0, paper_entry)

    # Save back to file
    try:
        with open(papers_file, 'w', encoding='utf-8') as f:
            json.dump(papers_data, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Successfully added paper '{paper.title}' to papers.json")
        print(f"   ID: {paper_id}")
        print(f"   Category: {category}")
        print(f"   Citations: {citations}")
    except Exception as e:
        print(f"Error saving to papers.json: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
