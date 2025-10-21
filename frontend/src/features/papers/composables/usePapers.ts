import { ref, computed, readonly } from 'vue'
import { arxivApi } from '@/services/arxivApi'
import type { ArxivPaper, ArxivSearchParams } from '../types'

export function useArxiv() {
  const papers = ref<ArxivPaper[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  const hasResults = computed(() => papers.value.length > 0)
  const hasError = computed(() => error.value !== null)
  
  const clearResults = () => {
    papers.value = []
    error.value = null
  }
  
  const searchPapers = async (params: ArxivSearchParams) => {
    loading.value = true
    error.value = null
    
    try {
      papers.value = await arxivApi.searchPapers(params)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
    } finally {
      loading.value = false
    }
  }
  
  const getPaperById = async (arxivId: string) => {
    loading.value = true
    error.value = null
    
    try {
      const paper = await arxivApi.getPaperById(arxivId)
      papers.value = paper ? [paper] : []
      return paper
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
      return null
    } finally {
      loading.value = false
    }
  }
  
  const searchByTitle = async (title: string, maxResults = 10) => {
    loading.value = true
    error.value = null
    
    try {
      papers.value = await arxivApi.searchByTitle(title, maxResults)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
    } finally {
      loading.value = false
    }
  }
  
  const searchByAuthor = async (authorName: string, maxResults = 20) => {
    loading.value = true
    error.value = null
    
    try {
      papers.value = await arxivApi.searchByAuthor(authorName, maxResults)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
    } finally {
      loading.value = false
    }
  }
  
  const searchByCategory = async (category: string, maxResults = 20) => {
    loading.value = true
    error.value = null
    
    try {
      papers.value = await arxivApi.searchByCategory(category, maxResults)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
    } finally {
      loading.value = false
    }
  }
  
  const advancedSearch = async (searchCriteria: {
    title?: string
    author?: string
    abstract?: string
    category?: string
    maxResults?: number
  }) => {
    loading.value = true
    error.value = null

    try {
      papers.value = await arxivApi.advancedSearch(searchCriteria)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
    } finally {
      loading.value = false
    }
  }

  const searchWithPerplexity = async (query: string, maxResults = 10) => {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/v1/papers/search/perplexity', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          max_results: maxResults
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Search failed')
      }

      // Get papers from arXiv API using the IDs returned by Perplexity
      if (data.arxiv_ids && data.arxiv_ids.length > 0) {
        const arxivPapers: ArxivPaper[] = []

        for (const arxivId of data.arxiv_ids) {
          try {
            const paper = await arxivApi.getPaperById(arxivId)
            if (paper) {
              arxivPapers.push(paper)
            }
          } catch (err) {
            console.warn(`Failed to fetch paper ${arxivId}:`, err)
          }
        }

        papers.value = arxivPapers
        console.log(`Fetched ${arxivPapers.length} papers from ${data.arxiv_ids.length} arXiv IDs`)
      } else {
        papers.value = []
        console.warn('No arXiv IDs returned from Perplexity search')
      }

      return papers.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      papers.value = []
      return []
    } finally {
      loading.value = false
    }
  }
  
  return {
    papers: readonly(papers),
    loading: readonly(loading),
    error: readonly(error),
    hasResults,
    hasError,
    clearResults,
    searchPapers,
    getPaperById,
    searchByTitle,
    searchByAuthor,
    searchByCategory,
    advancedSearch,
    searchWithPerplexity
  }
}