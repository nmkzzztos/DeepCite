import { useWorkspaceStore } from '../stores/workspaceStore'
import { storeToRefs } from 'pinia'

export function useWorkspace() {
  const store = useWorkspaceStore()
  
  const {
    workspaces,
    currentWorkspace,
    currentWorkspaceId,
    isLoading,
    error,
    workspaceCount,
    embeddingModels,
    defaultEmbeddingModel,
    embeddingStats
  } = storeToRefs(store)

  const {
    fetchWorkspaces,
    createWorkspace,
    selectWorkspace,
    deleteWorkspace,
    uploadDocument,
    deleteDocument,
    fetchEmbeddingModels,
    fetchEmbeddingStats
  } = store

  return {
    // State
    workspaces,
    currentWorkspace,
    currentWorkspaceId,
    isLoading,
    error,
    workspaceCount,
    embeddingModels,
    defaultEmbeddingModel,
    embeddingStats,
    
    // Actions
    fetchWorkspaces,
    createWorkspace,
    selectWorkspace,
    deleteWorkspace,
    uploadDocument,
    deleteDocument,
    fetchEmbeddingModels,
    fetchEmbeddingStats,
  }
}