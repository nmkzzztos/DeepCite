<template>
  <div class="min-h-screen -to-br from-slate-50 to-white px-6 py-8">
    <div class="max-w-7xl mx-auto">
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-24">
        <div class="loading-spinner"></div>
        <p class="mt-4 text-slate-600 font-medium">Loading workspace...</p>
      </div>

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

      <div v-else-if="!currentWorkspace" class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-6">
          <FolderX class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-xl font-medium text-slate-800 mb-2">Workspace not found</h3>
        <p class="text-slate-600 mb-8 max-w-md">
          The workspace you're looking for doesn't exist or has been deleted.
        </p>
        <BaseButton
          variant="primary"
          size="lg"
          @click="$router.push('/workspaces')"
        >
          Back to Workspaces
        </BaseButton>
      </div>

      <div v-else class="workspace-content">
        <!-- Workspace Header -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-12">
          <div class="mb-6 sm:mb-0">
            <div class="flex items-center gap-3 mb-4">
              <button
                @click="$router.push('/workspaces')"
                class="flex items-center gap-2 text-slate-600 hover:text-slate-800 transition-colors duration-200"
              >
                <ArrowLeft class="w-4 h-4" />
                <span class="text-sm font-medium">Workspaces</span>
              </button>
              <ChevronRight class="w-4 h-4 text-slate-400" />
              <span class="text-sm font-medium text-slate-800">{{ currentWorkspace.name }}</span>
            </div>

            <h1 class="text-3xl font-light text-slate-800 tracking-tight mb-2">{{ currentWorkspace.name }}</h1>
            <p v-if="currentWorkspace.description" class="text-slate-600 text-lg font-light mb-4">
              {{ currentWorkspace.description }}
            </p>

            <div class="flex items-center gap-6">
              <div class="flex items-center gap-2 text-slate-500 text-sm">
                <FileText class="w-4 h-4" />
                <span>{{ currentWorkspace.documentCount || 0 }} documents</span>
              </div>
              <div class="flex items-center gap-2 text-slate-500 text-sm">
                <Database class="w-4 h-4" />
                <span>{{ currentWorkspace.embeddingCount || 0 }} embeddings</span>
              </div>
            </div>
          </div>

          <BaseButton
            variant="primary"
            size="md"
            :icon-left="Upload"
            @click="showUploadModal = true"
          >
            Upload Document
          </BaseButton>
        </div>

        <!-- Documents Section -->
        <div class="">
          <div v-if="documents.length === 0" class="flex flex-col items-center justify-center py-16 text-center">
            <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-6">
              <FileText class="w-8 h-8 text-slate-400" />
            </div>
            <h3 class="text-xl font-medium text-slate-800 mb-2">No documents yet</h3>
            <p class="text-slate-600 mb-8 max-w-md">
              Upload your first document to start analyzing with AI
            </p>
            <BaseButton
              variant="primary"
              size="lg"
              :icon-left="Upload"
              @click="showUploadModal = true"
            >
              Upload Document
            </BaseButton>
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div
              v-for="document in documents"
              :key="document.id"
              class="group bg-white border border-slate-200 rounded-xl p-6 hover:border-slate-300 hover:shadow-lg transition-all duration-200 cursor-pointer relative overflow-hidden"
              @click="handleViewDocument(document)"
            >
              <!-- Subtle gradient overlay -->
              <div class="absolute inset-0 bg-gradient-to-br from-slate-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

              <!-- Header -->
              <div class="flex items-start justify-between mb-4 relative z-10">
                <div class="flex items-center gap-3">
                  <div class="p-2 w-15 h-15 bg-slate-100 rounded-lg flex items-center justify-center group-hover:bg-slate-200 transition-colors duration-200">
                    <FileText class="w-5 h-5 text-slate-600" />
                  </div>
                  <h3 class="text-lg font-medium text-slate-800 group-hover:text-slate-900 transition-colors duration-200 line-clamp-1">
                    {{ document.title || document.filename }}
                  </h3>
                </div>

                <div class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">

                  <button
                    @click.stop="handleDeleteDocument(document.id)"
                    class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
                    :title="'Delete document'"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Content -->
              <div class="mb-4 relative z-10">
                <p class="text-slate-600 text-sm font-mono mb-3 truncate">
                  {{ document.filename }}
                </p>

                <div class="flex flex-wrap gap-3 text-xs text-slate-500">
                  <div class="flex items-center gap-1">
                    <Calendar class="w-3 h-3" />
                    <span>{{ formatDate(document.uploadedAt) }}</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <HardDrive class="w-3 h-3" />
                    <span>{{ formatFileSize(document.fileSize) }}</span>
                  </div>
                  <div v-if="document.pageCount" class="flex items-center gap-1">
                    <BookOpen class="w-3 h-3" />
                    <span>{{ document.pageCount }} pages</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>

        <!-- PDF Viewer -->
        <div v-if="isPdfViewerOpen" class="fixed top-0 right-0 w-250px h-screen bg-white border-l border-slate-200 shadow-xl z-40">
          <PdfViewer
            :pdf-data="currentPdfData"
            :document-title="currentPdfTitle"
            :is-visible="isPdfViewerOpen"
            @close="closePdfViewer"
            @error="handlePdfError"
          />
        </div>
      </div>

      <!-- Upload Modal -->
      <DocumentUploadModal
        :is-open="showUploadModal"
        :workspace-id="workspaceId"
        @close="showUploadModal = false"
        @uploaded="handleDocumentUploaded"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeft,
  ChevronRight,
  Upload,
  FileText,
  Database,
  FolderX,
  AlertCircle,
  Calendar,
  HardDrive,
  BookOpen,
  Trash2
} from 'lucide-vue-next'
import { BaseButton } from '../../../shared/components'
import { useWorkspace } from '../composables/useWorkspace'
import DocumentUploadModal from '../components/DocumentUploadModal.vue'
import { PdfViewer, usePdfViewer, type PdfDocument } from '@/features/pdfViewer'
import type { Document } from '@/shared/types'

const route = useRoute()
const showUploadModal = ref(false)

// Workspace composable
const {
  currentWorkspace,
  isLoading,
  error,
  fetchWorkspaces,
  selectWorkspace,
  deleteDocument
} = useWorkspace()

// PDF Viewer composable
const {
  currentPdf,
  isViewerOpen: isPdfViewerOpen,
  openPdf,
  closePdf: closePdfViewer
} = usePdfViewer()

// Computed properties
const workspaceId = computed(() => route.params.id as string)
const documents = computed(() => currentWorkspace.value?.documents || [])
const currentPdfData = computed(() => currentPdf.value?.base64Data || undefined)
const currentPdfTitle = computed(() => currentPdf.value?.title || '')

// Helper functions
const isValidBase64 = (str: string): boolean => {
  try {
    // Check if string contains only valid base64 characters
    const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/
    return base64Regex.test(str) && str.length % 4 === 0
  } catch {
    return false
  }
}

const base64ToUint8Array = (base64: string): Uint8Array => {
  // Remove any whitespace and ensure proper padding
  const cleanBase64 = base64.replace(/\s/g, '')
  const paddedBase64 = cleanBase64.padEnd(Math.ceil(cleanBase64.length / 4) * 4, '=')

  try {
    // For large files, use chunked processing to avoid memory issues
    if (paddedBase64.length > 1000000) { // More than ~750KB
      console.log('Using chunked base64 processing for large file')
      return base64ToUint8ArrayChunked(paddedBase64)
    }

    // Use built-in atob for smaller files
    const binaryString = atob(paddedBase64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    return bytes
  } catch (error) {
    console.error('atob failed, trying alternative method:', error)

    // Alternative method using TextDecoder
    try {
      const binaryString = atob(paddedBase64)
      const encoder = new TextEncoder()
      const uint8Array = encoder.encode(binaryString)
      return uint8Array
    } catch (fallbackError) {
      console.error('Fallback method also failed:', fallbackError)
      throw new Error('All base64 conversion methods failed')
    }
  }
}

const base64ToUint8ArrayChunked = (base64: string): Uint8Array => {
  // Process base64 in chunks to avoid memory issues
  const chunkSize = 100000 // Process in 100KB chunks
  const totalLength = Math.floor(base64.length / 4) * 3
  const result = new Uint8Array(totalLength)

  let resultOffset = 0

  for (let i = 0; i < base64.length; i += chunkSize) {
    const chunk = base64.slice(i, i + chunkSize)
    const paddedChunk = chunk.padEnd(Math.ceil(chunk.length / 4) * 4, '=')
    const binaryString = atob(paddedChunk)
    const chunkBytes = new Uint8Array(binaryString.length)

    for (let j = 0; j < binaryString.length; j++) {
      chunkBytes[j] = binaryString.charCodeAt(j)
    }

    result.set(chunkBytes, resultOffset)
    resultOffset += chunkBytes.length

    // Allow UI to update during processing
    if (i % (chunkSize * 10) === 0) {
      console.log(`Processed ${(i / base64.length * 100).toFixed(1)}% of base64 data`)
    }
  }

  return result
}

const isPdfHeader = (bytes: Uint8Array): boolean => {
  // PDF files start with %PDF-
  return bytes.length >= 4 &&
         bytes[0] === 0x25 && // %
         bytes[1] === 0x50 && // P
         bytes[2] === 0x44 && // D
         bytes[3] === 0x46    // F
}

// Methods
const handleDocumentUploaded = (document: Document) => {
  // Document list will be refreshed automatically by the upload function
  console.log('Document uploaded successfully:', document)
}


const handleViewDocument = async (document: Document) => {
  try {
    // Try the base64 method first
    try {
      await loadDocumentViaBase64(document)
    } catch (base64Error) {
      console.warn('Base64 method failed, trying download method:', base64Error)

      // Fallback to download method
      await loadDocumentViaDownload(document)
    }
  } catch (error) {
    console.error('Error opening document:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
    alert(`Failed to open document: ${errorMessage}`)
  }
}

const loadDocumentViaBase64 = async (document: Document) => {
  // Fetch document as base64
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${apiBaseUrl}/api/v1/documents/${document.id}/view`
  const response = await fetch(url)

  if (!response.ok) {
    const errorText = await response.text()
    console.error('Server error:', errorText)
    throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`)
  }

  const contentType = response.headers.get('content-type')
  if (!contentType || !contentType.includes('application/json')) {
    throw new Error('Server returned invalid response format')
  }

  const data = await response.json()

  // Check if server rejected base64 due to file size
  if (data.use_download || (data.error && data.error.includes('too large'))) {
    console.warn('Server rejected base64 due to file size, using download fallback')
    throw new Error(`Server: ${data.error || 'File too large for base64'}`)
  }

  if (!data.base64) {
    throw new Error('Invalid response: missing base64 data')
  }

  // Check file size - for large files, throw error to use fallback
  const fileSizeMB = (data.file_size || 0) / (1024 * 1024)
  if (fileSizeMB > 1) { // More than 1MB
    console.warn(`File too large for base64 (${fileSizeMB.toFixed(2)}MB), using fallback method`)
    throw new Error(`File too large for base64 processing: ${fileSizeMB.toFixed(2)}MB`)
  }

  // Validate base64 string
  if (!isValidBase64(data.base64)) {
    throw new Error('Invalid base64 format received from server')
  }

  console.log('Base64 length:', data.base64.length)
  console.log('Base64 starts with:', data.base64.substring(0, 50))
  console.log('Original file size:', data.file_size, 'bytes')

  // Convert base64 to Uint8Array using a more robust method
  let bytes: Uint8Array
  try {
    bytes = base64ToUint8Array(data.base64)
  } catch (conversionError) {
    console.error('Base64 conversion error:', conversionError)
    throw new Error('Failed to convert base64 to binary data')
  }

  console.log('Converted to bytes, length:', bytes.length)

  // Verify PDF header
  if (bytes.length < 4 || !isPdfHeader(bytes)) {
    console.error('Invalid PDF header:', bytes.slice(0, 4))
    throw new Error('Received data is not a valid PDF file')
  }

  // Create PDF document object
  const pdfDocument: PdfDocument = {
    id: document.id,
    title: document.title || document.filename,
    filename: document.filename,
    base64Data: bytes,
    mimetype: data.mimetype || 'application/pdf'
  }

  // Open in PDF viewer
  openPdf(pdfDocument)
}

const loadDocumentViaDownload = async (document: Document) => {
  // Fetch document as binary blob
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${apiBaseUrl}/api/v1/documents/${document.id}/download`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to download document: ${response.status} ${response.statusText}`)
  }

  const blob = await response.blob()
  const arrayBuffer = await blob.arrayBuffer()
  const bytes = new Uint8Array(arrayBuffer)

  console.log('Downloaded via blob, size:', bytes.length)

  // Verify PDF header
  if (bytes.length < 4 || !isPdfHeader(bytes)) {
    console.error('Invalid PDF header from download:', bytes.slice(0, 4))
    throw new Error('Downloaded file is not a valid PDF')
  }

  // Create PDF document object
  const pdfDocument: PdfDocument = {
    id: document.id,
    title: document.title || document.filename,
    filename: document.filename,
    base64Data: bytes,
    mimetype: 'application/pdf'
  }

  // Open in PDF viewer
  openPdf(pdfDocument)
}

const handleDeleteDocument = async (documentId: string) => {
  if (confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
    try {
      await deleteDocument(workspaceId.value, documentId, true) // Delete completely
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }
}

const handlePdfError = (error: string) => {
  console.error('PDF Viewer Error:', error)
  alert(`Failed to load PDF: ${error}`)
}


const formatDate = (date: Date | string) => {
  const targetDate = typeof date === 'string' ? new Date(date) : date
  return targetDate.toLocaleDateString()
}

const formatFileSize = (bytes: number) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 Bytes'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// Watch for workspace ID changes
watch(workspaceId, (newId) => {
  if (newId) {
    selectWorkspace(newId)
  }
}, { immediate: true })

// Initialize
onMounted(() => {
  if (workspaceId.value) {
    selectWorkspace(workspaceId.value)
  }
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

/* Custom scrollbar for better aesthetics */
.documents-grid {
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}

.documents-grid::-webkit-scrollbar {
  width: 6px;
}

.documents-grid::-webkit-scrollbar-track {
  background: transparent;
}

.documents-grid::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.documents-grid::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Line clamp utility for text truncation */
.line-clamp-1 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

/* Smooth focus transitions for accessibility */
button:focus,
input:focus {
  outline: 2px solid #1d4ed8;
  outline-offset: 2px;
}

/* Subtle backdrop blur effect for modal */
.modal-overlay {
  backdrop-filter: blur(4px);
}
</style>