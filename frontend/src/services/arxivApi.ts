import axios from 'axios'
import type { ArxivAuthor, ArxivPaper, ArxivSearchParams } from '@/features/arxiv/types'

class ArxivApiService {
  private readonly baseUrl = 'https://export.arxiv.org/api/query'

  /**
   * Search arXiv papers by various criteria
   */
  async searchPapers(params: ArxivSearchParams): Promise<ArxivPaper[]> {
    const searchParams = new URLSearchParams()
    
    if (params.query) {
      searchParams.append('search_query', params.query)
    }
    
    if (params.idList && params.idList.length > 0) {
      searchParams.append('id_list', params.idList.join(','))
    }
    
    if (params.start !== undefined) {
      searchParams.append('start', params.start.toString())
    }
    
    if (params.maxResults !== undefined) {
      searchParams.append('max_results', params.maxResults.toString())
    }
    
    if (params.sortBy) {
      searchParams.append('sortBy', params.sortBy)
    }
    
    if (params.sortOrder) {
      searchParams.append('sortOrder', params.sortOrder)
    }

    try {
      const response = await axios.get(`${this.baseUrl}?${searchParams.toString()}`, {
        headers: {
          'Accept': 'application/atom+xml'
        }
      })
      
      return this.parseArxivResponse(response.data)
    } catch (error) {
      console.error('Error fetching from arXiv:', error)
      throw new Error('Failed to fetch papers from arXiv')
    }
  }

  /**
   * Get a paper by arXiv ID
   */
  async getPaperById(arxivId: string): Promise<ArxivPaper | null> {
    const papers = await this.searchPapers({ idList: [arxivId] })
    return papers.length > 0 ? papers[0] : null
  }

  /**
   * Search papers by title
   */
  async searchByTitle(title: string, maxResults = 10): Promise<ArxivPaper[]> {
    return this.searchPapers({
      query: `ti:"${title}"`,
      maxResults,
      sortBy: 'relevance'
    })
  }

  /**
   * Search papers by author
   */
  async searchByAuthor(authorName: string, maxResults = 20): Promise<ArxivPaper[]> {
    return this.searchPapers({
      query: `au:"${authorName}"`,
      maxResults,
      sortBy: 'lastUpdatedDate',
      sortOrder: 'descending'
    })
  }

  /**
   * Search papers by category
   */
  async searchByCategory(category: string, maxResults = 20): Promise<ArxivPaper[]> {
    return this.searchPapers({
      query: `cat:${category}`,
      maxResults,
      sortBy: 'lastUpdatedDate',
      sortOrder: 'descending'
    })
  }

  /**
   * Advanced search with multiple criteria
   */
  async advancedSearch({
    title,
    author,
    abstract,
    category,
    maxResults = 20
  }: {
    title?: string
    author?: string
    abstract?: string
    category?: string
    maxResults?: number
  }): Promise<ArxivPaper[]> {
    const queryParts: string[] = []
    
    if (title) queryParts.push(`ti:"${title}"`)
    if (author) queryParts.push(`au:"${author}"`)
    if (abstract) queryParts.push(`abs:"${abstract}"`)
    if (category) queryParts.push(`cat:${category}`)
    
    if (queryParts.length === 0) {
      throw new Error('At least one search criterion must be provided')
    }
    
    const query = queryParts.join(' AND ')
    
    return this.searchPapers({
      query,
      maxResults,
      sortBy: 'relevance'
    })
  }

  /**
   * Parse arXiv XML response to structured data
   */
  private parseArxivResponse(xmlData: string): ArxivPaper[] {
    const parser = new DOMParser()
    const doc = parser.parseFromString(xmlData, 'text/xml')
    const entries = doc.querySelectorAll('entry')
    
    const papers: ArxivPaper[] = []
    
    entries.forEach(entry => {
      try {
        const paper = this.parseEntry(entry)
        if (paper) papers.push(paper)
      } catch (error) {
        console.warn('Error parsing arXiv entry:', error)
      }
    })
    
    return papers
  }

  private parseEntry(entry: Element): ArxivPaper | null {
    const getId = (text: string) => text.split('/').pop()?.replace('v', '') || text
    
    const id = getId(entry.querySelector('id')?.textContent || '')
    const title = entry.querySelector('title')?.textContent?.trim().replace(/\s+/g, ' ') || ''
    const summary = entry.querySelector('summary')?.textContent?.trim().replace(/\s+/g, ' ') || ''
    const published = entry.querySelector('published')?.textContent || ''
    const updated = entry.querySelector('updated')?.textContent || ''
    
    // Parse authors
    const authorElements = entry.querySelectorAll('author')
    const authors: ArxivAuthor[] = []
    authorElements.forEach(authorEl => {
      const name = authorEl.querySelector('name')?.textContent?.trim()
      const affiliation = authorEl.querySelector('affiliation')?.textContent?.trim()
      if (name) {
        authors.push({ name, affiliation })
      }
    })
    
    // Parse categories
    const categoryElements = entry.querySelectorAll('category')
    const categories: string[] = []
    let primaryCategory = ''
    
    categoryElements.forEach((catEl, index) => {
      const term = catEl.getAttribute('term')
      if (term) {
        categories.push(term)
        if (index === 0) primaryCategory = term
      }
    })
    
    // Parse links
    const linkElements = entry.querySelectorAll('link')
    let pdfUrl = ''
    let abstractUrl = ''
    
    linkElements.forEach(linkEl => {
      const href = linkEl.getAttribute('href') || ''
      const type = linkEl.getAttribute('type')
      const title = linkEl.getAttribute('title')
      
      if (type === 'application/pdf' || title === 'pdf') {
        pdfUrl = href
      } else if (href.includes('abs/')) {
        abstractUrl = href
      }
    })
    
    // Parse optional fields
    const doi = entry.querySelector('arxiv\\:doi, doi')?.textContent?.trim()
    const journalRef = entry.querySelector('arxiv\\:journal_ref, journal_ref')?.textContent?.trim()
    const comment = entry.querySelector('arxiv\\:comment, comment')?.textContent?.trim()
    
    if (!id || !title) return null
    
    return {
      id,
      title,
      summary,
      authors,
      published,
      updated,
      categories,
      primaryCategory,
      pdfUrl,
      abstractUrl,
      doi,
      journalRef,
      comment
    }
  }
}

export const arxivApi = new ArxivApiService()