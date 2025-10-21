export interface ArxivAuthor {
  name: string
  affiliation?: string
}

export interface ArxivPaper {
  id: string
  title: string
  summary: string
  authors: ArxivAuthor[]
  published: string
  updated: string
  categories: string[]
  primaryCategory: string
  pdfUrl: string
  abstractUrl: string
  doi?: string
  journalRef?: string
  comment?: string
}

export interface ArxivSearchParams {
  query?: string
  idList?: string[]
  start?: number
  maxResults?: number
  sortBy?: 'relevance' | 'lastUpdatedDate' | 'submittedDate'
  sortOrder?: 'ascending' | 'descending'
}

export interface PaperImportData {
  paper: ArxivPaper
  workspaceId: string
  embeddingModelId?: string
}