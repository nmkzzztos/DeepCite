<template>
  <div v-if="isOpen" class="modal-overlay" @click="handleOverlayClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>Select Workspaces & Documents</h3>
        <button @click="close" class="close-button">
          <X class="close-icon" />
        </button>
      </div>

      <div class="modal-body">
        <div v-if="isLoading" class="loading-state">
          <div class="spinner"></div>
          <p>Loading workspaces...</p>
        </div>

        <div v-else-if="error" class="error-state">
          <AlertCircle class="error-icon" />
          <p>{{ error }}</p>
          <button @click="loadWorkspaces" class="retry-button">Retry</button>
        </div>

        <div v-else class="workspace-list">
          <div v-if="workspaces.length === 0" class="empty-state">
            <p>No workspaces available</p>
          </div>

          <div v-for="workspace in workspaces" :key="workspace.id" class="workspace-item">
            <div class="workspace-header">
              <label class="workspace-checkbox">
                <input
                  type="checkbox"
                  :checked="isWorkspaceSelected(workspace.id)"
                  @change="toggleWorkspace(workspace.id)"
                />
                <span class="checkmark"></span>
                <span class="workspace-name">{{ workspace.name }}</span>
                <span class="document-count">({{ workspace.documentCount || 0 }} docs)</span>
              </label>
              
              <button
                v-if="isWorkspaceSelected(workspace.id)"
                @click="toggleWorkspaceExpanded(workspace.id)"
                class="expand-button"
              >
                <ChevronDown 
                  class="expand-icon" 
                  :class="{ 'expanded': expandedWorkspaces.has(workspace.id) }"
                />
              </button>
            </div>

            <div 
              v-if="isWorkspaceSelected(workspace.id) && expandedWorkspaces.has(workspace.id)"
              class="documents-list"
            >
              <div v-if="!workspace.documents && isWorkspaceSelected(workspace.id)" class="loading-documents">
                <div class="mini-spinner"></div>
                <span>Loading documents...</span>
              </div>

              <div v-else-if="workspace.documents?.length === 0" class="no-documents">
                <p>No documents in this workspace</p>
              </div>

              <div v-else class="document-items">
                <label 
                  v-for="document in workspace.documents" 
                  :key="document.id"
                  class="document-checkbox"
                >
                  <input
                    type="checkbox"
                    :checked="isDocumentSelected(workspace.id, document.id)"
                    @change="toggleDocument(workspace.id, document.id)"
                  />
                  <span class="checkmark"></span>
                  <div class="document-info">
                    <span class="document-title">{{ document.title || document.filename }}</span>
                    <span class="document-meta">
                      {{ document.pageCount ? `${document.pageCount} pages` : '' }}
                      {{ document.authors ? ` • ${document.authors.join(', ')}` : '' }}
                      {{ document.year ? ` • ${document.year}` : '' }}
                    </span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <div class="selection-summary">
          <span>{{ selectedWorkspaceCount }} workspaces, {{ selectedDocumentCount }} documents selected</span>
        </div>
        
        <div class="modal-actions">
          <button @click="clearSelection" class="clear-button">Clear All</button>
          <button @click="close" class="cancel-button">Cancel</button>
          <button @click="applySelection" class="apply-button">Apply Selection</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { X, ChevronDown, AlertCircle } from 'lucide-vue-next'
import { useWorkspaceStore } from '../../workspaces/stores/workspaceStore'
import type { Workspace, Document } from '@/shared/types'

interface Props {
  isOpen: boolean
  initialSelection?: {
    workspaces: string[]
    documents: Record<string, string[]>
  }
}

interface Emits {
  (e: 'close'): void
  (e: 'apply', selection: {
    workspaces: string[]
    documents: Record<string, string[]>
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const workspaceStore = useWorkspaceStore()

// State
const isLoading = ref(false)
const error = ref<string | null>(null)
const selectedWorkspaces = ref<Set<string>>(new Set())
const selectedDocuments = ref<Record<string, Set<string>>>({})
const expandedWorkspaces = ref<Set<string>>(new Set())

// Computed
const workspaces = computed(() => workspaceStore.workspaces)

const selectedWorkspaceCount = computed(() => selectedWorkspaces.value.size)

const selectedDocumentCount = computed(() => {
  return Object.values(selectedDocuments.value).reduce(
    (total, docSet) => total + docSet.size, 
    0
  )
})

// Methods
const loadWorkspaces = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    await workspaceStore.fetchWorkspaces()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load workspaces'
  } finally {
    isLoading.value = false
  }
}

const loadWorkspaceDocuments = async (workspaceId: string) => {
  try {
    await workspaceStore.fetchWorkspaceDetails(workspaceId)
  } catch (err) {
    console.error('Failed to load workspace documents:', err)
  }
}

const isWorkspaceSelected = (workspaceId: string) => {
  return selectedWorkspaces.value.has(workspaceId)
}

const isDocumentSelected = (workspaceId: string, documentId: string) => {
  return selectedDocuments.value[workspaceId]?.has(documentId) || false
}

const toggleWorkspace = async (workspaceId: string) => {
  if (selectedWorkspaces.value.has(workspaceId)) {
    // Deselect workspace and all its documents
    selectedWorkspaces.value.delete(workspaceId)
    delete selectedDocuments.value[workspaceId]
    expandedWorkspaces.value.delete(workspaceId)
  } else {
    // Select workspace
    selectedWorkspaces.value.add(workspaceId)
    selectedDocuments.value[workspaceId] = new Set()
    expandedWorkspaces.value.add(workspaceId)
    
    // Load documents if not already loaded
    const workspace = workspaces.value.find(w => w.id === workspaceId)
    if (workspace && !workspace.documents) {
      await loadWorkspaceDocuments(workspaceId)
    }
  }
}

const toggleDocument = (workspaceId: string, documentId: string) => {
  if (!selectedDocuments.value[workspaceId]) {
    selectedDocuments.value[workspaceId] = new Set()
  }
  
  if (selectedDocuments.value[workspaceId].has(documentId)) {
    selectedDocuments.value[workspaceId].delete(documentId)
  } else {
    selectedDocuments.value[workspaceId].add(documentId)
  }
}

const toggleWorkspaceExpanded = (workspaceId: string) => {
  if (expandedWorkspaces.value.has(workspaceId)) {
    expandedWorkspaces.value.delete(workspaceId)
  } else {
    expandedWorkspaces.value.add(workspaceId)
  }
}

const clearSelection = () => {
  selectedWorkspaces.value.clear()
  selectedDocuments.value = {}
  expandedWorkspaces.value.clear()
}

const applySelection = () => {
  const selection = {
    workspaces: Array.from(selectedWorkspaces.value),
    documents: Object.fromEntries(
      Object.entries(selectedDocuments.value).map(([workspaceId, docSet]) => [
        workspaceId,
        Array.from(docSet)
      ])
    )
  }
  
  emit('apply', selection)
  close()
}

const close = () => {
  emit('close')
}

const handleOverlayClick = (event: MouseEvent) => {
  if (event.target === event.currentTarget) {
    close()
  }
}

// Initialize selection from props
const initializeSelection = () => {
  if (props.initialSelection) {
    selectedWorkspaces.value = new Set(props.initialSelection.workspaces)
    selectedDocuments.value = Object.fromEntries(
      Object.entries(props.initialSelection.documents).map(([workspaceId, docs]) => [
        workspaceId,
        new Set(docs)
      ])
    )
    // Expand selected workspaces
    props.initialSelection.workspaces.forEach(id => {
      expandedWorkspaces.value.add(id)
    })
  }
}

// Watchers
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    loadWorkspaces()
    initializeSelection()
  }
})

// Load workspaces on mount if modal is already open
onMounted(() => {
  if (props.isOpen) {
    loadWorkspaces()
    initializeSelection()
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 800px;
  max-height: 80vh;
  width: 90vw;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.close-button {
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.5rem;
  color: var(--color-text-muted);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.close-button:hover {
  background-color: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #dc2626;
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.close-button:active {
  transform: scale(0.95);
}

.close-icon {
  width: 1.125rem;
  height: 1.125rem;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  max-height: calc(80vh - 140px);
}

/* Custom scrollbar styles */
.modal-body::-webkit-scrollbar {
  width: 6px;
}

.modal-body::-webkit-scrollbar-track {
  background: var(--color-background-secondary);
  border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-focus);
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  text-align: center;
}

.spinner {
  width: 1.75rem;
  height: 1.75rem;
  border: 2px solid var(--color-border);
  border-top: 2px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 0.75rem;
}

.mini-spinner {
  width: 0.875rem;
  height: 0.875rem;
  border: 1px solid var(--color-border);
  border-top: 1px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 0.375rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  width: 1.75rem;
  height: 1.75rem;
  color: var(--color-error);
  margin-bottom: 0.75rem;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 0.875rem;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  color: white;
  border: 1px solid var(--color-primary);
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
  position: relative;
  overflow: hidden;
}

.retry-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.retry-button:hover {
  background: linear-gradient(135deg, var(--color-primary-hover) 0%, #1d4ed8 100%);
  border-color: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}

.retry-button:hover::before {
  left: 100%;
}

.retry-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-state {
  text-align: center;
  padding: 1.5rem;
  color: var(--color-text-muted);
}

.workspace-item {
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  overflow: hidden;
  transition: all 0.2s ease;
}

.workspace-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(29, 78, 216, 0.1);
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem;
  background-color: var(--color-background-secondary);
  border-bottom: 1px solid var(--color-border);
}

.workspace-checkbox,
.document-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  flex: 1;
}

.workspace-checkbox input,
.document-checkbox input {
  display: none;
}

.checkmark {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--color-border);
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.workspace-checkbox input:checked + .checkmark,
.document-checkbox input:checked + .checkmark {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.workspace-checkbox input:checked + .checkmark::after,
.document-checkbox input:checked + .checkmark::after {
  content: '✓';
  color: white;
  font-size: 0.875rem;
  font-weight: bold;
}

.workspace-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.document-count {
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

.expand-button {
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0.375rem;
  border-radius: 0.375rem;
  color: var(--color-text-muted);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.expand-button:hover {
  background-color: rgba(29, 78, 216, 0.08);
  border-color: var(--color-primary);
  color: var(--color-primary);
  transform: scale(1.05);
}

.expand-button:active {
  transform: scale(0.95);
}

.expand-icon {
  width: 1.125rem;
  height: 1.125rem;
  transition: transform 0.2s ease;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.documents-list {
  border-top: 1px solid var(--color-border);
  background-color: var(--color-background);
}

.loading-documents {
  display: flex;
  align-items: center;
  padding: 0.75rem 0.875rem;
  color: var(--color-text-muted);
}

.no-documents {
  padding: 0.75rem 0.875rem;
  text-align: center;
  color: var(--color-text-muted);
}

.document-items {
  display: flex;
  flex-direction: column;
}

.document-checkbox {
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid var(--color-border);
  transition: all 0.2s ease;
}

.document-checkbox:last-child {
  border-bottom: none;
}

.document-checkbox:hover {
  background-color: rgba(29, 78, 216, 0.03);
  border-color: var(--color-primary);
}

.document-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.document-title {
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.document-meta {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 0.75rem 0.75rem;
}

.selection-summary {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
}

.clear-button,
.cancel-button,
.apply-button {
  padding: 0.5rem 0.875rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.clear-button {
  background-color: transparent;
  color: var(--color-text-muted);
  border-color: var(--color-border);
}

.clear-button:hover {
  border-color: #f59e0b;
  background-color: rgba(245, 158, 11, 0.1);
  color: #d97706;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

.clear-button:active {
  transform: translateY(0);
}

.cancel-button {
  background-color: transparent;
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.cancel-button:hover {
  border-color: var(--color-border-focus);
  background-color: rgba(29, 78, 216, 0.08);
  color: var(--color-primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
}

.cancel-button:active {
  transform: translateY(0);
}

.apply-button {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  color: white;
  border-color: var(--color-primary);
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}

.apply-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.apply-button:hover {
  background: linear-gradient(135deg, var(--color-primary-hover) 0%, #1d4ed8 100%);
  border-color: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}

.apply-button:hover::before {
  left: 100%;
}

.apply-button:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}
</style>