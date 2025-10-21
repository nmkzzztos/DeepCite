import { workspaceApi } from '@/features/workspaces/services/workspaceApi'
import type { ArxivPaper, PaperImportData } from '../types'

export class ArxivImportService {
  /**
   * Import an arXiv paper into a workspace by downloading the PDF
   */
  async importPaper(importData: PaperImportData): Promise<boolean> {
    const { paper, workspaceId, embeddingModelId } = importData
    
    try {
      // Download PDF from arXiv
      const pdfResponse = await fetch(paper.pdfUrl)
      if (!pdfResponse.ok) {
        throw new Error('Failed to download PDF from arXiv')
      }
      
      const pdfBlob = await pdfResponse.blob()
      const pdfFile = new File([pdfBlob], `${paper.id}.pdf`, { type: 'application/pdf' })
      
      // Extract year from published date
      const publishedYear = new Date(paper.published).getFullYear()
      
      // Prepare upload data
      const uploadData = {
        file: pdfFile,
        title: paper.title,
        authors: paper.authors.map(author => author.name),
        year: publishedYear,
        source: `arXiv:${paper.id}`,
        embedding_model_id: embeddingModelId
      }
      
      // Upload to workspace
      const result = await workspaceApi.uploadDocument(workspaceId, uploadData)
      return result.success || false
      
    } catch (error) {
      console.error('Error importing arXiv paper:', error)
      throw error
    }
  }
  
  /**
   * Check if a paper is already imported in a workspace
   */
  async isPaperImported(workspaceId: string, arxivId: string): Promise<boolean> {
    try {
      const documents = await workspaceApi.getWorkspaceDocuments(workspaceId)
      if (!documents.success || !documents.data) return false
      
      return documents.data.some((doc: any) =>
        doc.source === `arXiv:${arxivId}` ||
        doc.title?.includes(arxivId)
      )
    } catch (error) {
      console.error('Error checking if paper is imported:', error)
      return false
    }
  }
  
  /**
   * Get import suggestions based on paper metadata
   */
  getImportSuggestions(paper: ArxivPaper) {
    const suggestions = {
      filename: `${paper.id.replace('/', '_')}_${paper.title.substring(0, 50).replace(/[^a-zA-Z0-9]/g, '_')}.pdf`,
      tags: [
        paper.primaryCategory,
        ...paper.categories.slice(0, 3),
        'arXiv'
      ],
      metadata: {
        arxivId: paper.id,
        doi: paper.doi,
        journalRef: paper.journalRef,
        comment: paper.comment,
        categories: paper.categories,
        publishedDate: paper.published,
        updatedDate: paper.updated
      }
    }
    
    return suggestions
  }
}

export const arxivImportService = new ArxivImportService()