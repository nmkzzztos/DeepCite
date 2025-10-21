/**
 * API service for workspace operations
 */

export interface WorkspaceCreateRequest {
  name: string
  description?: string
}

export interface WorkspaceUpdateRequest {
  name?: string
  description?: string
}

export interface DocumentUploadRequest {
  file: File
  title?: string
  authors?: string[]
  year?: number
  source?: string
  embedding_model_id?: string
}

export interface ApiResponse<T> {
  success?: boolean
  error?: string
  data?: T
}

const API_BASE = '/api/v1'

class WorkspaceApiService {
  async getWorkspaces() {
    const response = await fetch(`${API_BASE}/workspaces`)
    if (!response.ok) {
      throw new Error(`Failed to fetch workspaces: ${response.statusText}`)
    }
    return response.json()
  }

  async getWorkspace(workspaceId: string) {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace: ${response.statusText}`)
    }
    return response.json()
  }

  async createWorkspace(data: WorkspaceCreateRequest) {
    const response = await fetch(`${API_BASE}/workspaces`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to create workspace')
    }
    
    return response.json()
  }

  async updateWorkspace(workspaceId: string, data: WorkspaceUpdateRequest) {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to update workspace')
    }
    
    return response.json()
  }

  async deleteWorkspace(workspaceId: string) {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
      method: 'DELETE',
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to delete workspace')
    }
    
    return response.json()
  }

  async uploadDocument(workspaceId: string, uploadData: DocumentUploadRequest) {
    const formData = new FormData()
    formData.append('file', uploadData.file)
    
    if (uploadData.title) {
      formData.append('title', uploadData.title)
    }
    
    if (uploadData.authors && uploadData.authors.length > 0) {
      formData.append('authors', JSON.stringify(uploadData.authors))
    }
    
    if (uploadData.year) {
      formData.append('year', uploadData.year.toString())
    }
    
    if (uploadData.source) {
      formData.append('source', uploadData.source)
    }
    
    if (uploadData.embedding_model_id) {
      formData.append('embedding_model_id', uploadData.embedding_model_id)
    }

    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/documents`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to upload document')
    }

    return response.json()
  }

  async deleteDocument(workspaceId: string, documentId: string, deleteCompletely = false) {
    const url = `${API_BASE}/workspaces/${workspaceId}/documents/${documentId}${
      deleteCompletely ? '?delete_completely=true' : ''
    }`
    
    const response = await fetch(url, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to delete document')
    }

    return response.json()
  }

  async getWorkspaceDocuments(workspaceId: string) {
    const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/documents`)
    if (!response.ok) {
      throw new Error(`Failed to fetch workspace documents: ${response.statusText}`)
    }
    return response.json()
  }

  async getEmbeddingModels() {
    const response = await fetch(`${API_BASE}/embedding-models`)
    if (!response.ok) {
      throw new Error(`Failed to fetch embedding models: ${response.statusText}`)
    }
    return response.json()
  }

  async getEmbeddingStats() {
    const response = await fetch(`${API_BASE}/embedding-stats`)
    if (!response.ok) {
      throw new Error(`Failed to fetch embedding stats: ${response.statusText}`)
    }
    return response.json()
  }
}

export const workspaceApi = new WorkspaceApiService()