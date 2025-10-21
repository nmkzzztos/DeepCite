import axios from 'axios'
import type { ArxivPaper } from '../types'

interface BackendCitationResponse {
  citations: Record<string, number | null>
  processed: number
}

class CitationService {
  private readonly backendBaseUrl = '/api/v1/citations'

  /**
   * Get citation count for a paper by DOI (legacy method - now uses backend)
   */
  async getCitationCountByDOI(doi: string): Promise<number | null> {
    try {
      const response = await axios.get<{ doi: string; citation_count: number | null }>(
        `${this.backendBaseUrl}/doi/${doi}`
      )

      return response.data.citation_count
    } catch (error) {
      console.warn(`Failed to get citation count for DOI ${doi}:`, error)
      return null
    }
  }

  /**
   * Get citation count for a paper by arXiv ID (legacy method - now uses backend)
   */
  async getCitationCountByArxivId(arxivId: string): Promise<number | null> {
    try {
      const response = await axios.get<{ citation_count: number | null }>(
        `${this.backendBaseUrl}/${arxivId}`
      )

      return response.data.citation_count
    } catch (error) {
      console.warn(`Failed to get citation count for arXiv ID ${arxivId}:`, error)
      return null
    }
  }

  /**
   * Get citation count for a paper by title (legacy method - now uses backend)
   */
  async getCitationCountByTitle(title: string): Promise<number | null> {
    try {
      const response = await axios.get<{ citation_count: number | null }>(
        `${this.backendBaseUrl}/title`,
        {
          params: { title }
        }
      )

      return response.data.citation_count
    } catch (error) {
      console.warn(`Failed to get citation count for title "${title}":`, error)
      return null
    }
  }

  /**
   * Get citation counts for multiple papers
   */
  async getCitationCounts(papers: ArxivPaper[]): Promise<Map<string, number>> {
    const citationMap = new Map<string, number>()

    try {
      // Prepare papers data for backend
      const papersData = papers.map(paper => ({
        id: paper.id,
        doi: paper.doi,
        title: paper.title
      }))

      // Send batch request to backend
      const response = await axios.post<BackendCitationResponse>(
        this.backendBaseUrl,
        { papers: papersData },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )

      // Process response
      const citations = response.data.citations
      Object.entries(citations).forEach(([paperId, citationCount]) => {
        if (citationCount !== null && citationCount !== undefined) {
          citationMap.set(paperId, citationCount)
        }
      })

    } catch (error) {
      console.warn('Failed to get citation counts from backend:', error)

      // Fallback: try individual requests if batch fails
      console.log('Falling back to individual requests...')
      for (const paper of papers) {
        try {
          let citationCount = null

          // Try arXiv ID first
          citationCount = await this.getCitationCountByArxivId(paper.id)

          // Try title as fallback
          if (citationCount === null) {
            citationCount = await this.getCitationCountByTitle(paper.title)
          }

          if (citationCount !== null) {
            citationMap.set(paper.id, citationCount)
          }

          // Small delay to avoid overwhelming the backend
          await new Promise(resolve => setTimeout(resolve, 200))
        } catch (err) {
          console.warn(`Failed to get citation for paper ${paper.id}:`, err)
        }
      }
    }

    return citationMap
  }

}

export const citationService = new CitationService()
