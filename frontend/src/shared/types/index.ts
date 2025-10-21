// Workspace types
export interface Workspace {
  id: string
  name: string
  description?: string
  documentCount?: number
  embeddingCount?: number
  paragraphCount?: number
  documents?: Document[]
  createdAt: Date | string
  updatedAt: Date | string
}

// Document types
export interface Document {
  id: string
  doc_id?: string // Backend uses doc_id
  filename: string
  title?: string
  authors?: string[]
  year?: number
  source?: string
  uploadedAt: Date | string
  fileSize: number
  pageCount?: number
  paragraphCount?: number
  embeddingCount?: number
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed'
  workspaceId?: string
  sha256?: string
  lang?: string
}

// Embedding model types
export interface EmbeddingModel {
  id: string
  name: string
  provider: string
  type: string
  description?: string
  embedding_dimension?: number
  supports_streaming?: boolean
}

export interface EmbeddingStats {
  total_embeddings: number
  models: Array<{
    model: string
    count: number
  }>
  collections: Array<{
    name: string
    count: number
    model: string
  }>
  available_models: EmbeddingModel[]
}

// Navigation types
export type NavigationSection = 'chat' | 'workspaces' | 'papers'