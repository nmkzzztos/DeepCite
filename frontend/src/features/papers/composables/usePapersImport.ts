import { ref, computed, readonly } from 'vue'
import { arxivImportService } from '../services/arxivImportService'
import { useWorkspaceStore } from '@/features/workspaces/stores/workspaceStore'
import type { ArxivPaper, PaperImportData } from '../types'

export function useArxivImport() {
  const workspaceStore = useWorkspaceStore()
  
  const importing = ref(false)
  const importError = ref<string | null>(null)
  const importedPapers = ref<Set<string>>(new Set())
  
  const currentWorkspace = computed(() => workspaceStore.currentWorkspace)
  const embeddingModels = computed(() => workspaceStore.embeddingModels)
  const defaultEmbeddingModel = computed(() => workspaceStore.defaultEmbeddingModel)
  
  const canImport = computed(() => {
    return currentWorkspace.value && !importing.value
  })
  
  const clearError = () => {
    importError.value = null
  }
  
  const importPaper = async (paper: ArxivPaper, workspaceId?: string, embeddingModelId?: string) => {
    if (!canImport.value && !workspaceId) {
      importError.value = 'No workspace selected'
      return false
    }
    
    importing.value = true
    importError.value = null
    
    try {
      const targetWorkspaceId = workspaceId || currentWorkspace.value!.id
      const targetEmbeddingModelId = embeddingModelId || defaultEmbeddingModel.value || undefined
      
      const importData: PaperImportData = {
        paper,
        workspaceId: targetWorkspaceId,
        embeddingModelId: targetEmbeddingModelId
      }
      
      const success = await arxivImportService.importPaper(importData)
      
      if (success) {
        importedPapers.value.add(paper.id)
        // Refresh workspace documents
        await workspaceStore.fetchWorkspaceDetails(targetWorkspaceId)
        return true
      } else {
        importError.value = 'Failed to import paper'
        return false
      }
    } catch (error) {
      importError.value = error instanceof Error ? error.message : 'Unknown error occurred'
      return false
    } finally {
      importing.value = false
    }
  }
  
  const checkIfImported = async (arxivId: string, workspaceId?: string) => {
    if (!workspaceId && !currentWorkspace.value) return false
    
    try {
      const targetWorkspaceId = workspaceId || currentWorkspace.value!.id
      const isImported = await arxivImportService.isPaperImported(targetWorkspaceId, arxivId)
      
      if (isImported) {
        importedPapers.value.add(arxivId)
      }
      
      return isImported
    } catch (error) {
      console.error('Error checking import status:', error)
      return false
    }
  }
  
  const isImported = (arxivId: string) => {
    return importedPapers.value.has(arxivId)
  }
  
  const getImportSuggestions = (paper: ArxivPaper) => {
    return arxivImportService.getImportSuggestions(paper)
  }
  
  const importMultiplePapers = async (papers: ArxivPaper[], workspaceId?: string, embeddingModelId?: string) => {
    const results = []
    
    for (const paper of papers) {
      const result = await importPaper(paper, workspaceId, embeddingModelId)
      results.push({ paper, success: result })
      
      // Small delay between imports to avoid overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    return results
  }
  
  return {
    importing: readonly(importing),
    importError: readonly(importError),
    importedPapers: readonly(importedPapers),
    currentWorkspace,
    embeddingModels,
    defaultEmbeddingModel,
    canImport,
    clearError,
    importPaper,
    checkIfImported,
    isImported,
    getImportSuggestions,
    importMultiplePapers
  }
}