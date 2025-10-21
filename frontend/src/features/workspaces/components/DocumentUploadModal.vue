<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click="handleOverlayClick">
    <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden" @click.stop>
      <div class="flex items-center justify-between p-6 border-b border-slate-200">
        <h2 class="text-2xl font-medium text-slate-800">Upload Document</h2>
        <button @click="closeModal" class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all duration-200">
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-6 space-y-6 overflow-y-auto max-h-[65vh]">
        <!-- File Selection -->
        <div class="space-y-3">
          <label class="block text-sm font-medium text-slate-700">Select PDF File</label>
          <div
            class="relative border-2 border-dashed border-slate-300 rounded-xl p-4 text-center cursor-pointer transition-all duration-200 hover:border-slate-400 hover:bg-slate-50/50"
            :class="{ 'border-slate-500 bg-slate-50': isDragOver }"
            @drop="handleDrop"
            @dragover.prevent="isDragOver = true"
            @dragleave="isDragOver = false"
            @click="triggerFileInput"
          >
            <div class="flex flex-row justify-center gap-10">
              <div class="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center">
                <Upload class="w-6 h-6 text-slate-600" />
              </div>
              <div v-if="!selectedFile" class="text-slate-600">
                <p class="font-medium">Drop your PDF file here</p>
                <p class="text-sm text-slate-500">or click to browse your files</p>
              </div>
              <div v-else class="flex items-center gap-3 text-slate-800">
                <FileText class="w-5 h-5 text-slate-600" />
                <div class="text-left">
                  <p class="font-medium title-truncate">{{ selectedFile.name }}</p>
                  <p class="text-sm text-slate-500">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
              </div>
            </div>
          </div>
          <input ref="fileInput" type="file" accept=".pdf" @change="handleFileSelect" class="hidden" />
        </div>

        <!-- Embedding Model Selection -->
        <div class="space-y-3">
          <label class="block text-sm font-medium text-slate-700">Embedding Model</label>
          <select
            v-model="selectedEmbeddingModel"
            class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 bg-white"
          >
            <option value="">Use default ({{ defaultEmbeddingModel || 'system default' }})</option>
            <option v-for="model in embeddingModels" :key="model.id" :value="model.id">
              {{ model.name }} ({{ model.provider }})
              <span v-if="model.embedding_dimension">
                - {{ model.embedding_dimension }}d
              </span>
            </option>
          </select>
          <p class="text-xs text-slate-500 leading-relaxed">
            Choose which embedding model to use for this document. Different models may provide different search quality.
          </p>
        </div>

        <!-- Optional Metadata -->
        <div class="space-y-4">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">Document Title (Optional)</label>
            <input
              v-model="documentTitle"
              type="text"
              class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
              placeholder="Enter document title..."
            />
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700">Authors (Optional)</label>
            <input
              v-model="documentAuthors"
              type="text"
              class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
              placeholder="Enter authors separated by commas..."
            />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="block text-sm font-medium text-slate-700">Year (Optional)</label>
              <input
                v-model.number="documentYear"
                type="number"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
                placeholder="2024"
                min="1900"
                :max="new Date().getFullYear()"
              />
            </div>

            <div class="space-y-2">
              <label class="block text-sm font-medium text-slate-700">Source (Optional)</label>
              <input
                v-model="documentSource"
                type="text"
                class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all duration-200 text-slate-800 placeholder-slate-400"
                placeholder="Journal, conference, etc."
              />
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-3 p-6 border-t border-slate-200 bg-slate-50/50">
        <BaseButton
          variant="primary"
          size="md"
          @click="closeModal"
          :disabled="isUploading"
        >
          Cancel
        </BaseButton>
        <BaseButton
          variant="primary"
          size="md"
          @click="handleUpload"
          :disabled="!selectedFile || isUploading"
        >
          <div v-if="isUploading" class="loading-spinner mr-2"></div>
          {{ isUploading ? 'Uploading...' : 'Upload Document' }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { X, Upload, FileText } from 'lucide-vue-next'
import { BaseButton } from '../../../shared/components'
import { useWorkspace } from '../composables/useWorkspace'

interface Props {
  isOpen: boolean
  workspaceId: string
}

interface Emits {
  (e: 'close'): void
  (e: 'uploaded', document: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Workspace composable
const {
  embeddingModels,
  defaultEmbeddingModel,
  uploadDocument,
  fetchEmbeddingModels
} = useWorkspace()

// Form state
const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const selectedEmbeddingModel = ref<string>('')
const documentTitle = ref<string>('')
const documentAuthors = ref<string>('')
const documentYear = ref<number | null>(null)
const documentSource = ref<string>('')
const isDragOver = ref(false)
const isUploading = ref(false)

// Methods
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragOver.value = false

  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (file.type === 'application/pdf') {
      selectedFile.value = file
    }
  }
}

const handleOverlayClick = (event: Event) => {
  if (event.target === event.currentTarget) {
    closeModal()
  }
}

const closeModal = () => {
  if (!isUploading.value) {
    resetForm()
    emit('close')
  }
}

const resetForm = () => {
  selectedFile.value = null
  selectedEmbeddingModel.value = ''
  documentTitle.value = ''
  documentAuthors.value = ''
  documentYear.value = null
  documentSource.value = ''
  isDragOver.value = false

  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleUpload = async () => {
  if (!selectedFile.value || !props.workspaceId) return

  isUploading.value = true

  try {
    const metadata: Record<string, any> = {}

    if (documentTitle.value.trim()) {
      metadata.title = documentTitle.value.trim()
    }

    if (documentAuthors.value.trim()) {
      metadata.authors = documentAuthors.value
        .split(',')
        .map(author => author.trim())
        .filter(author => author.length > 0)
    }

    if (documentYear.value) {
      metadata.year = documentYear.value
    }

    if (documentSource.value.trim()) {
      metadata.source = documentSource.value.trim()
    }

    const document = await uploadDocument(
      props.workspaceId,
      selectedFile.value,
      metadata,
      selectedEmbeddingModel.value || undefined
    )

    emit('uploaded', document)
    closeModal()
  } catch (error) {
    console.error('Upload failed:', error)
    // Error handling is done in the store
  } finally {
    isUploading.value = false
  }
}

const formatFileSize = (bytes: number) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 Bytes'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// Initialize
onMounted(() => {
  fetchEmbeddingModels()
})
</script>

<style scoped>
/* Custom animations and effects that can't be done with Tailwind */
.loading-spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Focus states for accessibility */
input:focus,
select:focus {
  box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.1);
}

/* Custom scrollbar for modal content */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.title-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}
</style>