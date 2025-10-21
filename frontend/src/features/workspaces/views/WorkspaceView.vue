<template>
  <div class="min-h-screen t-to-br from-slate-50 to-white px-6 py-8">
    <div class="max-w-7xl mx-auto">

      <!-- Header Section -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-12">
        <div class="mb-6 sm:mb-0">
          <h1 class="text-3xl font-light text-slate-800 tracking-tight">Workspaces</h1>
          <p class="mt-2 text-slate-600 text-lg font-light">
            Manage your document collections and AI-powered analysis
          </p>
        </div>
        <BaseButton
          v-if="workspaces.length > 0"
          variant="primary"
          size="md"
          :icon-left="Plus"
          @click="showCreateModal = true"
        >
          New Workspace
        </BaseButton>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-24">
        <div class="loading-spinner"></div>
        <p class="mt-4 text-slate-600 font-medium">Loading workspaces...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex flex-col items-center justify-center py-24 text-center">
        <AlertCircle class="w-12 h-12 text-slate-400 mb-4" />
        <p class="text-slate-700 font-medium mb-4">{{ error }}</p>
        <BaseButton
          variant="primary"
          size="md"
          @click="fetchWorkspaces"
        >
          Try Again
        </BaseButton>
      </div>

      <!-- Empty State -->
      <div v-else-if="workspaces.length === 0" class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-6">
          <FolderOpen class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-xl font-medium text-slate-800 mb-2">No workspaces yet</h3>
        <p class="text-slate-600 mb-8 max-w-md">
          Create your first workspace to start organizing documents and enable AI-powered analysis
        </p>
        <BaseButton
          variant="primary"
          size="lg"
          :icon-left="Plus"
          @click="showCreateModal = true"
        >
          Create Workspace
        </BaseButton>
      </div>

      <!-- Workspaces Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="workspace in workspaces"
          :key="workspace.id"
          class="group bg-white border border-slate-200 rounded-xl p-6 hover:border-slate-300 hover:shadow-lg transition-all duration-200 cursor-pointer relative overflow-hidden"
          @click="handleWorkspaceClick(workspace.id)"
        >
          <!-- Subtle gradient overlay -->
          <div class="absolute inset-0 bg-gradient-to-br from-slate-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

          <!-- Header -->
          <div class="flex items-start justify-between mb-4 relative z-10">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center group-hover:bg-slate-200 transition-colors duration-200">
                <Folder class="w-5 h-5 text-slate-600" />
              </div>
              <h3 class="text-lg font-medium text-slate-800 group-hover:text-slate-900 transition-colors duration-200">
                {{ workspace.name }}
              </h3>
            </div>

            <button
              @click.stop="handleDeleteWorkspace(workspace.id)"
              class="opacity-0 group-hover:opacity-100 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
              :title="'Delete workspace'"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>

          <!-- Description -->
          <div class="mb-4 relative z-10">
            <p v-if="workspace.description" class="text-slate-600 text-sm leading-relaxed">
              {{ workspace.description }}
            </p>
            <p v-else class="text-slate-400 text-sm italic">
              No description provided
            </p>
          </div>

          <!-- Stats -->
          <div class="flex items-center gap-4 mb-4 relative z-10">
            <div class="flex items-center gap-1.5 text-slate-500 text-sm">
              <FileText class="w-4 h-4" />
              <span>{{ workspace.documentCount || 0 }} documents</span>
            </div>
            <div class="flex items-center gap-1.5 text-slate-500 text-sm">
              <Database class="w-4 h-4" />
              <span>{{ workspace.embeddingCount || 0 }} embeddings</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="border-t border-slate-100 pt-3 relative z-10">
            <span class="text-xs text-slate-400 font-medium">
              Updated {{ formatRelativeTime(workspace.updatedAt) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Create Workspace Modal -->
      <div
        v-if="showCreateModal"
        class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click="showCreateModal = false"
      >
        <div
          class="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-hidden"
          @click.stop
        >
          <!-- Modal Header -->
          <div class="flex items-center justify-between p-6 border-b border-slate-200">
            <h2 class="text-xl font-medium text-slate-800">Create New Workspace</h2>
            <button
              @click="showCreateModal = false"
              class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors duration-200"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Modal Form -->
          <form @submit.prevent="handleCreateWorkspace" class="p-6 space-y-6">
            <div>
              <label for="workspace-name" class="block text-sm font-medium text-slate-700 mb-2">
                Workspace Name
              </label>
              <input
                id="workspace-name"
                v-model="newWorkspaceName"
                type="text"
                placeholder="Enter workspace name"
                required
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
              />
            </div>

            <div>
              <label for="workspace-description" class="block text-sm font-medium text-slate-700 mb-2">
                Description <span class="text-slate-500 font-normal">(optional)</span>
              </label>
              <textarea
                id="workspace-description"
                v-model="newWorkspaceDescription"
                placeholder="Describe what this workspace is for"
                rows="3"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400 resize-none"
              ></textarea>
            </div>

            <!-- Modal Actions -->
            <div class="flex items-center justify-end gap-3 pt-4">
              <BaseButton
                variant="ghost"
                size="md"
                @click="showCreateModal = false"
              >
                Cancel
              </BaseButton>
              <BaseButton
                variant="primary"
                size="md"
                type="submit"
                :disabled="!newWorkspaceName.trim()"
              >
                Create Workspace
              </BaseButton>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Plus,
  FolderOpen,
  Folder,
  FileText,
  Database,
  Trash2,
  X,
  AlertCircle
} from 'lucide-vue-next'
import { BaseButton } from '../../../shared/components'
import { useWorkspace } from '../composables/useWorkspace'

const router = useRouter()

// Workspace composable
const {
  workspaces,
  isLoading,
  error,
  fetchWorkspaces,
  createWorkspace,
  selectWorkspace,
  deleteWorkspace
} = useWorkspace()

// Modal state
const showCreateModal = ref(false)
const newWorkspaceName = ref('')
const newWorkspaceDescription = ref('')

// Methods
const handleWorkspaceClick = (workspaceId: string) => {
  selectWorkspace(workspaceId)
  router.push(`/workspace/${workspaceId}`)
}

const handleCreateWorkspace = async () => {
  try {
    await createWorkspace(newWorkspaceName.value, newWorkspaceDescription.value)
    showCreateModal.value = false
    newWorkspaceName.value = ''
    newWorkspaceDescription.value = ''
  } catch (error) {
    console.error('Failed to create workspace:', error)
  }
}

const handleDeleteWorkspace = async (workspaceId: string) => {
  if (confirm('Are you sure you want to delete this workspace? This action cannot be undone.')) {
    try {
      await deleteWorkspace(workspaceId)
    } catch (error) {
      console.error('Failed to delete workspace:', error)
    }
  }
}

const formatRelativeTime = (date: Date | string) => {
  const now = new Date()
  const targetDate = typeof date === 'string' ? new Date(date) : date
  const diffMs = now.getTime() - targetDate.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return targetDate.toLocaleDateString()
}

// Initialize
onMounted(() => {
  fetchWorkspaces()
})
</script>

<style scoped>
/* Custom animations and effects that can't be done with Tailwind */
.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 2px solid #e2e8f0;
  border-top: 2px solid #475569;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Smooth focus transitions for accessibility */
input:focus,
textarea:focus {
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.1);
}

/* Custom hover effects for workspace cards */
.workspace-card {
  position: relative;
}

.workspace-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.2s ease;
  border-radius: inherit;
  pointer-events: none;
}

.workspace-card:hover::before {
  opacity: 1;
}

/* Subtle backdrop blur effect for modal */
.modal-overlay {
  backdrop-filter: blur(4px);
}

/* Custom scrollbar for better aesthetics */
.workspaces-grid {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}

.workspaces-grid::-webkit-scrollbar {
  width: 6px;
}

.workspaces-grid::-webkit-scrollbar-track {
  background: transparent;
}

.workspaces-grid::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.workspaces-grid::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>