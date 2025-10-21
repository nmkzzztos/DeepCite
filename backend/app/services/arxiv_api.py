"""
ArXiv API service for DeepCite
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


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
    """Service for interacting with arXiv API"""

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
                    logger.error(f"arXiv API error: {response.status_code}")
                    return []

                return self._parse_arxiv_response(response.text)

        except Exception as e:
            logger.error(f"Error fetching from arXiv: {e}")
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
            logger.error(f"Error parsing arXiv response: {e}")
            return []

    def _parse_entry(self, entry) -> Optional[ArxivPaper]:
        """Parse individual arXiv entry"""
        try:
            # Extract basic fields
            id_elem = entry.find('.//{http://www.w3.org/2005/Atom}id')
            title_elem = entry.find('.//{http://www.w3.org/2005/Atom}title')
            summary_elem = entry.find('.//{http://www.w3.org/2005/Atom}summary')
            published_elem = entry.find('.//{http://www.w3.org/2005/Atom}published')
            updated_elem = entry.find('.//{http://www.w3.org/2005/Atom}updated')

            if not id_elem or not title_elem:
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
            author_elements = entry.findall('.//{http://www.w3.org/2005/Atom}author')
            for author_elem in author_elements:
                name_elem = author_elem.find('.//{http://www.w3.org/2005/Atom}name')
                if name_elem is not None and name_elem.text:
                    name = name_elem.text.strip()
                    # Try to get affiliation
                    affiliation = None
                    affiliation_elem = author_elem.find('.//{http://arxiv.org/schemas/atom}affiliation')
                    if affiliation_elem is not None:
                        affiliation = affiliation_elem.text.strip()
                    authors.append(ArxivAuthor(name, affiliation))

            # Parse categories
            categories = []
            primary_category = ''
            category_elements = entry.findall('.//{http://www.w3.org/2005/Atom}category')
            for i, cat_elem in enumerate(category_elements):
                term = cat_elem.get('term', '')
                if term:
                    categories.append(term)
                    if i == 0:  # First category is primary
                        primary_category = term

            # Parse links
            pdf_url = ''
            abstract_url = ''
            link_elements = entry.findall('.//{http://www.w3.org/2005/Atom}link')
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

            doi_elem = entry.find('.//{http://arxiv.org/schemas/atom}doi')
            if doi_elem is not None:
                doi = doi_elem.text.strip()

            journal_elem = entry.find('.//{http://arxiv.org/schemas/atom}journal_ref')
            if journal_elem is not None:
                journal_ref = journal_elem.text.strip()

            comment_elem = entry.find('.//{http://arxiv.org/schemas/atom}comment')
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
            logger.warning(f"Error parsing arXiv entry: {e}")
            return None
