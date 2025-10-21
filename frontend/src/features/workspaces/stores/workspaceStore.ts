import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Workspace, EmbeddingModel, EmbeddingStats } from '@/shared/types'
import { workspaceApi } from '../services/workspaceApi'

export interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspaceId: string | null
  isLoading: boolean
  error: string | null
  embeddingModels: EmbeddingModel[]
  defaultEmbeddingModel: string | null
  embeddingStats: EmbeddingStats | null
}

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const workspaces = ref<Workspace[]>([])
  const currentWorkspaceId = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const embeddingModels = ref<EmbeddingModel[]>([])
  const defaultEmbeddingModel = ref<string | null>(null)
  const embeddingStats = ref<EmbeddingStats | null>(null)

  // Getters
  const currentWorkspace = computed(() => 
    workspaces.value.find(w => w.id === currentWorkspaceId.value) || null
  )

  const workspaceCount = computed(() => workspaces.value.length)

  // Actions
  const fetchWorkspaces = async () => {
    isLoading.value = true
    error.value = null
    
    try {
      const data = await workspaceApi.getWorkspaces()
      workspaces.value = data.workspaces || []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      console.error('Failed to fetch workspaces:', err)
    } finally {
      isLoading.value = false
    }
  }

  const createWorkspace = async (name: string, description?: string) => {
    isLoading.value = true
    error.value = null

    try {
      const newWorkspace = await workspaceApi.createWorkspace({ name, description })
      workspaces.value.push(newWorkspace)
      currentWorkspaceId.value = newWorkspace.id
      
      return newWorkspace
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      console.error('Failed to create workspace:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const selectWorkspace = async (workspaceId: string) => {
    const workspace = workspaces.value.find(w => w.id === workspaceId)
    if (workspace) {
      currentWorkspaceId.value = workspaceId
      // Fetch detailed workspace data if not already loaded
      if (!workspace.documents) {
        await fetchWorkspaceDetails(workspaceId)
      }
    }
  }

  const deleteWorkspace = async (workspaceId: string) => {
    isLoading.value = true
    error.value = null

    try {
      await workspaceApi.deleteWorkspace(workspaceId)
      workspaces.value = workspaces.value.filter(w => w.id !== workspaceId)
      
      if (currentWorkspaceId.value === workspaceId) {
        currentWorkspaceId.value = workspaces.value.length > 0 ? workspaces.value[0].id : null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      console.error('Failed to delete workspace:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const uploadDocument = async (workspaceId: string, file: File, metadata?: Record<string, any>, embeddingModelId?: string) => {
    isLoading.value = true
    error.value = null

    try {
      const uploadData = {
        file,
        embedding_model_id: embeddingModelId,
        ...metadata
      }
      
      const result = await workspaceApi.uploadDocument(workspaceId, uploadData)
      
      // Refresh workspace data to get updated document list
      await fetchWorkspaceDetails(workspaceId)

      return result.document
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      console.error('Failed to upload document:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchWorkspaceDetails = async (workspaceId: string) => {
    try {
      const workspace = await workspaceApi.getWorkspace(workspaceId)
      
      // Update workspace in the list
      const index = workspaces.value.findIndex(w => w.id === workspaceId)
      if (index !== -1) {
        workspaces.value[index] = workspace
      }
      
      return workspace
    } catch (err) {
      console.error('Failed to fetch workspace details:', err)
      throw err
    }
  }

  const deleteDocument = async (workspaceId: string, documentId: string, deleteCompletely = false) => {
    isLoading.value = true
    error.value = null

    try {
      await workspaceApi.deleteDocument(workspaceId, documentId, deleteCompletely)
      
      // Refresh workspace data
      await fetchWorkspaceDetails(workspaceId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error'
      console.error('Failed to delete document:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchEmbeddingModels = async () => {
    try {
      const data = await workspaceApi.getEmbeddingModels()
      embeddingModels.value = data.models || []
      defaultEmbeddingModel.value = data.default || null
    } catch (err) {
      console.error('Failed to fetch embedding models:', err)
      throw err
    }
  }

  const fetchEmbeddingStats = async () => {
    try {
      const stats = await workspaceApi.getEmbeddingStats()
      embeddingStats.value = stats
      return stats
    } catch (err) {
      console.error('Failed to fetch embedding stats:', err)
      throw err
    }
  }

  return {
    // State
    workspaces,
    currentWorkspaceId,
    isLoading,
    error,
    embeddingModels,
    defaultEmbeddingModel,
    embeddingStats,
    
    // Getters
    currentWorkspace,
    workspaceCount,
    
    // Actions
    fetchWorkspaces,
    createWorkspace,
    selectWorkspace,
    deleteWorkspace,
    uploadDocument,
    fetchWorkspaceDetails,
    deleteDocument,
    fetchEmbeddingModels,
    fetchEmbeddingStats,
  }
})