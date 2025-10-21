<template>
  <div>
    <!-- Main Search Form -->
    <div class="bg-white border border-slate-200 rounded-xl shadow-sm p-8">
    <!-- Header with toggle button -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-medium text-slate-800">Search Papers</h2>
      <button
        v-if="hasResults && !loading"
        @click="toggleResultsPanel"
        class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors duration-200"
        :class="isResultsPanelCollapsed ? 'bg-slate-100' : 'bg-blue-50 text-blue-700'"
      >
        <FileText class="w-4 h-4" />
        {{ isResultsPanelCollapsed ? 'Show Results' : 'Hide Results' }}
        <ChevronRight
          v-if="!isResultsPanelCollapsed"
          class="w-4 h-4 transition-transform duration-200"
        />
        <ChevronLeft
          v-else
          class="w-4 h-4 transition-transform duration-200"
        />
      </button>
    </div>

    <!-- Search Tabs -->
    <div class="flex gap-1 mb-8 border-b border-slate-200">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="[
          'px-6 py-3 text-sm font-medium transition-all duration-200 border-b-2',
          activeTab === tab.id
            ? 'text-slate-800 border-slate-800'
            : 'text-slate-600 border-transparent hover:text-slate-800 hover:border-slate-200'
        ]"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Search Content -->
    <div class="space-y-6">



      <!-- Advanced Search -->
      <div v-if="activeTab === 'advanced'" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            v-model="advancedSearch.title"
            type="text"
            placeholder="Title (optional)"
            class="px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
          />
          <input
            v-model="advancedSearch.author"
            type="text"
            placeholder="Author (optional)"
            class="px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
          />
          <input
            v-model="advancedSearch.abstract"
            type="text"
            placeholder="Abstract keywords (optional)"
            class="px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
          />
          <input
            v-model="advancedSearch.category"
            type="text"
            placeholder="Category (e.g., cs.AI, math.CO)"
            class="px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
          />
        </div>
        <div class="flex justify-end">
          <BaseButton
            @click="handleAdvancedSearch"
            :disabled="loading"
            variant="primary"
            size="md"
          >
            Advanced Search
          </BaseButton>
        </div>
      </div>

      <!-- AI Search with Perplexity -->
      <div v-if="activeTab === 'perplexity'" class="space-y-4">
        <div class="space-y-4">
          <textarea
            v-model="perplexityQuery"
            placeholder="Describe what papers you're looking for (e.g., 'recent papers on transformer architectures for language models')"
            class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400 resize-none"
            rows="4"
            @keydown.ctrl.enter="handlePerplexitySearch"
          ></textarea>
          <div class="flex items-center justify-between">
            <div class="text-sm text-slate-600">
              <Info class="w-4 h-4 inline mr-1" />
              Search powered by AI will find relevant arXiv papers and return them for import
            </div>
            <BaseButton
              @click="handlePerplexitySearch"
              :disabled="loading || !perplexityQuery.trim()"
              variant="primary"
              size="md"
            >
              AI Search
            </BaseButton>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-12 text-center">
      <div class="loading-spinner"></div>
      <p class="mt-4 text-slate-600 font-medium">Searching arXiv...</p>
    </div>

    <!-- Error State -->
    <div v-if="hasError" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div class="flex items-center gap-3">
        <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0" />
        <p class="text-red-800 text-sm">{{ error }}</p>
      </div>
    </div>

    <!-- Import Error State -->
    <div v-if="importError" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div class="flex items-center gap-3">
        <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0" />
        <p class="text-red-800 text-sm">Import Error: {{ importError }}</p>
      </div>
    </div>

  </div>

  <!-- Results Panel (Right Side) -->
  <div
    v-if="hasResults && !loading && !isResultsPanelCollapsed"
    class="fixed top-0 right-0 w-96 h-screen bg-white border-l border-slate-200 shadow-xl z-40 overflow-hidden transition-transform duration-300 ease-in-out"
    :class="{ 'translate-x-full': isResultsPanelCollapsed }"
  >
    <div class="flex flex-col h-full">
      <!-- Results Header -->
      <div class="flex items-center justify-between p-6 border-b border-slate-200 bg-slate-50">
        <div class="flex items-center gap-3">
          <FileText class="w-5 h-5 text-slate-600" />
          <h3 class="text-lg font-medium text-slate-800">{{ papers.length }} paper{{ papers.length === 1 ? '' : 's' }} found</h3>
        </div>
        <button
          @click="collapseResultsPanel"
          class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors duration-200"
          title="Hide results panel"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Bulk Actions (when papers selected) -->
      <div v-if="selectedPapers.length > 0" class="p-4 bg-blue-50 border-b border-blue-200">
        <div class="flex items-center justify-between">
          <span class="text-sm text-blue-800 font-medium">{{ selectedPapers.length }} selected</span>
          <BaseButton
            @click="showImportDialog = true"
            variant="primary"
            size="sm"
          >
            Import Selected
          </BaseButton>
        </div>
      </div>

      <!-- Results List -->
      <div class="flex-1 overflow-y-auto custom-scrollbar">
        <div class="divide-y divide-slate-100">
          <div
            v-for="paper in papers"
            :key="paper.id"
            class="p-4 hover:bg-slate-50 transition-colors duration-200"
          >
            <!-- Header with checkbox and expand button -->
            <div class="flex items-start gap-3 mb-3">
              <input
                type="checkbox"
                :checked="isSelected(paper.id)"
                @change="togglePaperSelection(paper as ArxivPaper)"
                class="mt-1 w-4 h-4 text-slate-600 bg-slate-100 border-slate-300 rounded focus:ring-slate-500 focus:ring-2"
              />
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-2 mb-2">
                  <h4 class="text-sm font-medium text-slate-800 line-clamp-2 flex-1">{{ paper.title }}</h4>
                  <button
                    @click="togglePaperExpansion(paper.id)"
                    class="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-colors duration-200 flex-shrink-0"
                    :aria-label="isExpanded(paper.id) ? 'Collapse paper details' : 'Expand paper details'"
                  >
                    <ChevronDown
                      v-if="!isExpanded(paper.id)"
                      class="w-4 h-4 transition-transform duration-200"
                    />
                    <ChevronUp
                      v-else
                      class="w-4 h-4 transition-transform duration-200"
                    />
                  </button>
                </div>

                <p class="text-xs text-slate-600 line-clamp-1 mb-2">
                  {{ paper.authors.map(a => a.name).join(', ') }}
                </p>

                <!-- Meta info -->
                <div class="flex items-center justify-between text-xs text-slate-500 mb-3">
                  <span>{{ formatDate(paper.published) }}</span>
                  <span class="bg-slate-100 px-2 py-1 rounded">{{ paper.primaryCategory }}</span>
                </div>

                <!-- Summary (truncated when collapsed, full when expanded) -->
                <div class="mb-3">
                  <p
                    class="text-xs text-slate-600"
                    :class="isExpanded(paper.id) ? '' : 'line-clamp-3'"
                  >
                    {{ isExpanded(paper.id) ? paper.summary : truncateText(paper.summary, 150) }}
                  </p>
                </div>

                <!-- Actions -->
                <div class="flex gap-2">
                  <a
                    :href="paper.abstractUrl"
                    target="_blank"
                    class="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-800 transition-colors duration-200"
                  >
                    <ExternalLink class="w-3 h-3" />
                    Abstract
                  </a>
                  <a
                    :href="paper.pdfUrl"
                    target="_blank"
                    class="inline-flex items-center gap-1 text-xs text-slate-600 hover:text-slate-800 transition-colors duration-200"
                  >
                    <Download class="w-3 h-3" />
                    PDF
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

    <!-- Import Dialog -->
    <div
      v-if="showImportDialog"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click="showImportDialog = false"
    >
      <div
        class="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="flex items-center justify-between p-6 border-b border-slate-200">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              <FileText class="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <h2 class="text-xl font-medium text-slate-800">Import Papers to Workspace</h2>
              <p class="text-sm text-slate-600 mt-1">{{ selectedPapers.length }} paper{{ selectedPapers.length === 1 ? '' : 's' }} selected for import</p>
            </div>
          </div>
          <button
            @click="showImportDialog = false"
            class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors duration-200"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Modal Content -->
        <div class="overflow-y-auto max-h-[60vh]">
          <!-- Selected Papers Preview -->
          <div class="p-6 border-b border-slate-200">
            <div class="flex items-center justify-between mb-4">
              <span class="text-sm font-medium text-slate-700">Selected Papers:</span>
              <span class="text-sm text-slate-500 bg-slate-100 px-2 py-1 rounded-md">{{ selectedPapers.length }}</span>
            </div>
            <div class="space-y-3">
              <div v-for="paper in selectedPapers.slice(0, 3)" :key="paper.id" class="bg-slate-50 rounded-lg p-3">
                <div class="text-sm font-medium text-slate-800 line-clamp-2 mb-1">{{ paper.title }}</div>
                <div class="text-xs text-slate-600 line-clamp-1">{{ paper.authors.map(a => a.name).join(', ') }}</div>
              </div>
              <div v-if="selectedPapers.length > 3" class="text-sm text-slate-500 text-center py-2">
                +{{ selectedPapers.length - 3 }} more paper{{ selectedPapers.length - 3 === 1 ? '' : 's' }}
              </div>
            </div>
          </div>

          <!-- Workspace Selection -->
          <div class="p-6 border-b border-slate-200">
            <div class="space-y-3">
              <div class="flex items-center gap-3">
                <Folder class="w-5 h-5 text-slate-600" />
                <label for="import-workspace-select" class="text-sm font-medium text-slate-700">Choose Workspace</label>
              </div>
              <select
                id="import-workspace-select"
                v-model="importWorkspaceId"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 bg-white"
              >
                <option value="">Select a workspace...</option>
                <option v-for="workspace in workspaceStore.workspaces" :key="workspace.id" :value="workspace.id">
                  {{ workspace.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Embedding Model Selection -->
          <div class="p-6 border-b border-slate-200">
            <div class="space-y-3">
              <div class="flex items-center gap-3">
                <Brain class="w-5 h-5 text-slate-600" />
                <label for="import-embedding-select" class="text-sm font-medium text-slate-700">Embedding Model (Optional)</label>
              </div>
              <select
                id="import-embedding-select"
                v-model="importEmbeddingModelId"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 bg-white"
              >
                <option value="">Use default model</option>
                <option v-for="model in embeddingModels" :key="model.id" :value="model.id">
                  {{ model.name }}
                </option>
              </select>
            </div>
          </div>

          <!-- Import Info -->
          <div class="p-6 bg-slate-50">
            <div class="flex items-center gap-3">
              <Info class="w-4 h-4 text-slate-600 flex-shrink-0" />
              <span class="text-sm text-slate-600">Papers will be processed and indexed for search</span>
            </div>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="flex items-center justify-end gap-3 p-6 bg-slate-50 border-t border-slate-200">
          <BaseButton
            variant="ghost"
            size="md"
            @click="showImportDialog = false"
          >
            Cancel
          </BaseButton>
          <BaseButton
            @click="handleBulkImport"
            :disabled="!importWorkspaceId || bulkImporting"
            variant="primary"
            size="md"
            :icon-left="bulkImporting ? Loader2 : Upload"
          >
            {{ bulkImporting ? 'Importing...' : 'Import Papers' }}
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useArxiv } from '../composables/usePapers'
import { useArxivImport } from '../composables/usePapersImport'
import { useWorkspaceStore } from '@/features/workspaces/stores/workspaceStore'
import { BaseButton } from '../../../shared/components'
import type { ArxivPaper } from '../types'
import {
  FileText,
  X,
  Folder,
  Brain,
  Info,
  Upload,
  Loader2,
  AlertCircle,
  ExternalLink,
  Download,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  ChevronLeft
} from 'lucide-vue-next'

interface Props {
  workspaceId?: string
  showWorkspaceSelector?: boolean
}

withDefaults(defineProps<Props>(), {
  showWorkspaceSelector: true
})

const emit = defineEmits<{
  paperSelected: [paper: ArxivPaper]
  paperImported: [paper: ArxivPaper, workspaceId: string]
}>()

const { papers, loading, error, hasResults, hasError, advancedSearch: performAdvancedSearch, searchWithPerplexity } = useArxiv()
const { importError, embeddingModels, importPaper, clearError } = useArxivImport()
const workspaceStore = useWorkspaceStore()

const activeTab = ref('advanced')
const selectedPapers = ref<ArxivPaper[]>([])
const expandedPapers = ref<Set<string>>(new Set())
const showImportDialog = ref(false)
const importWorkspaceId = ref<string>('')
const importEmbeddingModelId = ref<string>('')
const bulkImporting = ref(false)
const perplexityQuery = ref('')
const isResultsPanelCollapsed = ref(false)

const advancedSearch = reactive({
  title: '',
  author: '',
  abstract: '',
  category: ''
})

const tabs = [
  { id: 'advanced', label: 'Advanced Search' },
  { id: 'perplexity', label: 'AI Search' }
]

// Initialize workspace store
onMounted(async () => {
  await workspaceStore.fetchWorkspaces()
  await workspaceStore.fetchEmbeddingModels()
})

// Clear selections and expand panel when papers change
watch(papers, () => {
  selectedPapers.value = []
  expandedPapers.value.clear()
  // Auto-expand results panel when new results are loaded
  if (papers.value.length > 0) {
    isResultsPanelCollapsed.value = false
  }
}, { immediate: true })


const handleAdvancedSearch = () => {
  const hasAnyField = Object.values(advancedSearch).some(value => value.trim())
  if (hasAnyField) {
    performAdvancedSearch(advancedSearch)
  }
}

const handlePerplexitySearch = () => {
  if (perplexityQuery.value.trim()) {
    searchWithPerplexity(perplexityQuery.value.trim())
  }
}

// Paper selection functions
const togglePaperSelection = (paper: ArxivPaper) => {
  const index = selectedPapers.value.findIndex(p => p.id === paper.id)
  if (index > -1) {
    selectedPapers.value.splice(index, 1)
  } else {
    selectedPapers.value.push(paper)
  }
}

const isSelected = (paperId: string) => {
  return selectedPapers.value.some(p => p.id === paperId)
}


const truncateText = (text: string, maxLength: number) => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Bulk import functions
const handleBulkImport = async () => {
  if (!importWorkspaceId.value || selectedPapers.value.length === 0) {
    return
  }

  bulkImporting.value = true
  clearError()

  try {
    let successCount = 0

    for (const paper of selectedPapers.value) {
      const success = await importPaper(
        paper,
        importWorkspaceId.value,
        importEmbeddingModelId.value || undefined
      )

      if (success) {
        successCount++
        // Emit event for each successfully imported paper
        emit('paperImported', paper, importWorkspaceId.value)
      }

      // Small delay between imports
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    if (successCount > 0) {
      selectedPapers.value = []
      showImportDialog.value = false
      importWorkspaceId.value = ''
      importEmbeddingModelId.value = ''
    }
  } catch (error) {
    console.error('Bulk import error:', error)
  } finally {
    bulkImporting.value = false
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const clearResults = () => {
  // Clear the results by triggering a new empty search or clearing the papers array
  // This will hide the right-side panel
  selectedPapers.value = []
  expandedPapers.value.clear()
  isResultsPanelCollapsed.value = false // Reset panel state when clearing results
  // You could also emit an event to clear results or call a method to reset the search
}

const collapseResultsPanel = () => {
  isResultsPanelCollapsed.value = true
}

const toggleResultsPanel = () => {
  isResultsPanelCollapsed.value = !isResultsPanelCollapsed.value
}

// Paper expansion functions
const togglePaperExpansion = (paperId: string) => {
  if (expandedPapers.value.has(paperId)) {
    expandedPapers.value.delete(paperId)
  } else {
    expandedPapers.value.add(paperId)
  }
}

const isExpanded = (paperId: string) => {
  return expandedPapers.value.has(paperId)
}

</script>

<style scoped>
/* Loading spinner */
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

/* Line clamp utilities */
.line-clamp-1 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.line-clamp-2 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.line-clamp-3 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

/* Focus styles for accessibility */
input:focus,
select:focus,
button:focus {
  outline: 2px solid #1d4ed8;
  outline-offset: 2px;
}

/* Custom scrollbar styles */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 #f8fafc;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #f8fafc;
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.custom-scrollbar::-webkit-scrollbar-thumb:active {
  background: #64748b;
}

.custom-scrollbar::-webkit-scrollbar-corner {
  background: #f8fafc;
}

/* Smooth transitions */
* {
  transition-property: color, background-color, border-color, transform, opacity;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 200ms;
}
</style>