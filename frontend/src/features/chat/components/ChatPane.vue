<template>
  <div class="chat-pane" :class="{ 'chat-pane--with-pdf': isPdfViewerOpen }">
    <div class="chat-pane__content">
      <div class="chat-pane__header">
        <div class="chat-pane__title">
          <h2>{{ currentConversation?.title || 'New Chat' }}</h2>
        </div>

        <div class="chat-pane__controls">
          <button
            v-if="chatMode === 'workspaces'"
            @click="showWorkspaceSelector = true"
            class="workspace-selector-button"
            :class="{ 'active': selectedWorkspaceCount > 0 || selectedDocumentCount > 0 }"
          >
            <Database class="workspace-icon" />
            <span v-if="selectedWorkspaceCount === 0">Select Sources</span>
            <span v-else>
              {{ selectedWorkspaceCount }} workspace{{ selectedWorkspaceCount !== 1 ? 's' : '' }}
              <span v-if="selectedDocumentCount > 0">, {{ selectedDocumentCount }} doc{{ selectedDocumentCount !== 1 ? 's' : '' }}</span>
            </span>
          </button>

          <button
            v-if="chatMode === 'internet'"
            @click="showDomainSelector = true"
            class="domain-selector-button"
            :class="{ 'active': selectedDomainCount > 0 }"
          >
            <Globe class="domain-icon" />
            <span v-if="selectedDomainCount === 0">Select Domains</span>
            <span v-else>{{ selectedDomainCount }} domain{{ selectedDomainCount !== 1 ? 's' : '' }}</span>
          </button>

          <select
            v-model="selectedModelId"
            @change="handleModelChange"
            class="model-select"
          >
            <option v-for="model in availableModels" :key="model.id" :value="model.id">
              {{ model.name }} ({{ model.provider }})
            </option>
          </select>
        </div>
      </div>

      <div class="chat-pane__messages" ref="messagesContainer">
      <div v-if="!currentConversation || currentConversation.messages.length === 0" class="chat-pane__empty">
        <div class="empty-state">
          <img src="/logo.svg" class="empty-state__icon" />
          <h3>Start a conversation</h3>
          <p>Choose a model and send your first message to begin chatting.</p>
        </div>
      </div>
      
      <div v-else class="messages-list">
        <div 
          v-for="message in currentConversation.messages" 
          :key="message.id"
          class="message"
          :class="{ 'message--user': message.role === 'user', 'message--assistant': message.role === 'assistant' }"
        >
          <div v-if="message.role === 'assistant'" class="message__avatar">
            <img src="/logo.svg" class="avatar-icon avatar-icon-bot" />
          </div>
          
          <div class="message__content">
            <!-- Context indicator for assistant messages -->
            <div v-if="message.role === 'assistant' && message.contextUsed" class="context-indicator">
              <Database class="context-icon" />
              <span>Response based on selected documents</span>
            </div>
            
            <div class="message__text">
              <div v-if="message.role === 'user'" class="message__plain-text">
                {{ message.content }}
              </div>
              <div v-else-if="message.content === '...'" class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div
                v-else
                class="message__html-content"
                v-html="message.htmlContent || message.content"
              ></div>
            </div>
            
            <!-- Search Results for assistant messages -->
            <SearchResults
              v-if="message.role === 'assistant' && message.searchResults"
              :search-results="message.searchResults"
              :on-open-pdf="handleSearchResultPdfOpen"
            />

            <!-- Citations for assistant messages -->
            <CitationsList
              v-if="message.role === 'assistant' && message.formattedCitations && message.formattedCitations.length > 0"
              :citations="message.formattedCitations"
              :total-cost="getUsageCost(message)"
              :on-open-pdf="handleCitationPdfOpen"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="chat-pane__input">
      <div v-if="error" class="error-message">
        <AlertCircle class="error-icon" />
        <span>{{ error }}</span>
        <button @click="clearError" class="error-dismiss">
          <X class="dismiss-icon" />
        </button>
      </div>

      <!-- Mode Switcher -->
      <div class="mode-switcher">
        <button
          @click="handleModeSwitch('normal')"
          :class="['mode-button', { 'active': chatMode === 'normal' }]"
          title="Normal Chat"
        >
          <MessageSquare class="mode-icon" />
          <span v-if="chatMode === 'normal'" class="mode-label">Normal</span>
        </button>

        <button
          @click="handleModeSwitch('workspaces')"
          :class="['mode-button', { 'active': chatMode === 'workspaces' }]"
          title="Chat with Documents"
        >
          <FolderOpen class="mode-icon" />
          <span v-if="chatMode === 'workspaces'" class="mode-label">Workspaces</span>
        </button>

        <button
          @click="handleModeSwitch('internet')"
          :class="['mode-button', { 'active': chatMode === 'internet' }]"
          title="Internet Search"
        >
          <Globe class="mode-icon" />
          <span v-if="chatMode === 'internet'" class="mode-label">Internet</span>
        </button>
      </div>

      <form @submit.prevent="handleSendMessage" class="input-form">
        <div class="input-container">
          <textarea
            v-model="messageInput"
            @keydown="handleKeyDown"
            :placeholder="getPlaceholderText()"
            class="message-input"
            rows="1"
            ref="textareaRef"
          ></textarea>

          <button
            type="submit"
            :disabled="!messageInput.trim() || isLoading"
            class="send-button"
          >
            <Send class="send-icon" />
          </button>
        </div>
      </form>
    </div>
    </div>

    <!-- PDF Viewer Panel -->
    <div v-if="isPdfViewerOpen" class="chat-pane__pdf-panel">
      <PdfViewer
        :pdf-data="currentPdfData"
        :document-title="currentPdfTitle"
        :is-visible="isPdfViewerOpen"
        :highlight-text="highlightText"
        :highlight-page="highlightPage"
        @close="handleClosePdfViewer"
        @error="handlePdfError"
      />
    </div>

    <!-- Workspace Document Selector Modal -->
    <WorkspaceDocumentSelector
      :is-open="showWorkspaceSelector"
      :initial-selection="currentWorkspaceSelection"
      @close="showWorkspaceSelector = false"
      @apply="handleWorkspaceSelectionApply"
    />

    <!-- Domain Selector Modal -->
    <DomainSelector
      :is-open="showDomainSelector"
      :initial-selection="selectedDomains"
      @close="showDomainSelector = false"
      @apply="handleDomainSelectionApply"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { Send, AlertCircle, X, Database, Globe, MessageSquare, FolderOpen } from 'lucide-vue-next'
import { useChatStore } from '../stores/chatStore'
import WorkspaceDocumentSelector from './WorkspaceDocumentSelector.vue'
import DomainSelector from './DomainSelector.vue'
import SearchResults from './SearchResults.vue'
import CitationsList from './CitationsList.vue'
import { PdfViewer, usePdfViewer } from '../../pdfViewer'

const chatStore = useChatStore()

// Reactive refs
const messageInput = ref('')
const messagesContainer = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()
const showWorkspaceSelector = ref(false)
const showDomainSelector = ref(false)
const chatMode = ref(chatStore.chatMode)

// PDF Viewer composable
const {
  currentPdf,
  isViewerOpen: isPdfViewerOpen,
  openPdf,
  closePdf
} = usePdfViewer()

// Computed properties
const currentConversation = computed(() => chatStore.currentConversation)
const availableModels = computed(() => chatStore.availableModels)
const selectedModelId = computed({
  get: () => chatStore.selectedModelId,
  set: (value) => chatStore.setSelectedModel(value)
})
// const selectedModel = computed(() =>
//   availableModels.value.find(m => m.id === selectedModelId.value)
// )
const isLoading = computed(() => chatStore.isLoading)
const error = computed(() => chatStore.error)

const currentWorkspaceSelection = computed(() => {
  if (!currentConversation.value) return { workspaces: [], documents: {} }
  return {
    workspaces: currentConversation.value.selectedWorkspaces || [],
    documents: currentConversation.value.selectedDocuments || {}
  }
})

const selectedWorkspaceCount = computed(() => {
  return currentWorkspaceSelection.value.workspaces.length
})

const selectedDocumentCount = computed(() => {
  return Object.values(currentWorkspaceSelection.value.documents).reduce(
    (total, docs) => total + docs.length,
    0
  )
})

const selectedDomains = computed(() => chatStore.selectedDomains)
const selectedDomainCount = computed(() => selectedDomains.value.length)

// PDF computed properties
const currentPdfData = computed(() => currentPdf.value?.base64Data || undefined)
const currentPdfTitle = computed(() => currentPdf.value?.title || '')

// PDF highlight state
const highlightText = ref<string>('')
const highlightPage = ref<number>(0)

// Methods
const handleSendMessage = async () => {
  const message = messageInput.value.trim()
  if (!message || isLoading.value) return

  messageInput.value = ''
  await chatStore.sendMessage(message)
  
  // Auto-resize textarea
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}

const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSendMessage()
  }
  
  // Auto-resize textarea
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
      textareaRef.value.style.height = textareaRef.value.scrollHeight + 'px'
    }
  })
}

const handleModelChange = () => {
  // Model change is handled by the computed setter
}

const clearError = () => {
  chatStore.clearError()
}

const handleWorkspaceSelectionApply = (selection: { workspaces: string[], documents: Record<string, string[]> }) => {
  chatStore.setWorkspaceSelection(selection.workspaces, selection.documents)
}

const handleModeSwitch = (mode: 'normal' | 'workspaces' | 'internet') => {
  chatMode.value = mode
}

const handleDomainSelectionApply = (domains: string[]) => {
  chatStore.setSelectedDomains(domains)
  showDomainSelector.value = false
}

const getPlaceholderText = () => {
  switch (chatMode.value) {
    case 'workspaces':
      return 'Ask questions about your selected documents...'
    case 'internet':
      return 'Ask questions to search the internet...'
    case null:
      return 'Type your message...'
    default:
      return 'Type your message...'
  }
}

const getUsageCost = (message: any): string | undefined => {
  // Extract cost from usage metadata if available
  if (message.usage && typeof message.usage === 'object') {
    const usage = message.usage
    if (usage.cost && typeof usage.cost === 'object') {
      return usage.cost.total_cost?.toString()
    }
  }
  return undefined
}

// Removed handleCitationClick and scrollToCitationInList functions
// Citations are now handled through the CitationsList component directly

const handleSearchResultPdfOpen = async (result: any, index: number) => {
  console.log('Search result PDF open clicked:', { result, index })
  console.log('Search result data:', {
    page: result.page,
    text: result.text?.substring(0, 100),
    document: result.document,
    paragraph_id: result.paragraph_id
  })

  try {
    // Ensure we have a valid page number
    const targetPage = result.page && result.page > 0 ? result.page : 1
    console.log('Using target page:', targetPage)

    // Set highlight data before loading PDF
    highlightText.value = result.text || ''
    highlightPage.value = targetPage

    console.log('Set highlight data from search result:', {
      text: highlightText.value.substring(0, 100),
      page: highlightPage.value,
      originalPage: result.page,
      targetPage: targetPage
    })

    // Load the PDF for this search result
    await loadDocumentForSource(result)
    console.log('PDF loaded successfully for search result:', result.document.title)
  } catch (error) {
    console.error('Error loading PDF for search result:', error)
    // Could show an error message to user
  }
}

const handleCitationPdfOpen = async (citation: any) => {
  console.log('Citation PDF open clicked:', citation)

  try {
    // For citations, we need to find the corresponding search result
    // Find the message that has both formattedCitations and searchResults
    const currentMessage = currentConversation.value?.messages.find(msg =>
      msg.role === 'assistant' &&
      msg.formattedCitations &&
      msg.searchResults &&
      msg.formattedCitations.length > 0 &&
      msg.searchResults.length > 0
    )

    if (currentMessage && currentMessage.searchResults) {
      console.log('Found message with search results:', currentMessage.searchResults.length)
      console.log('Citation index:', citation.index)

      const searchResult = currentMessage.searchResults[citation.index - 1] // Arrays are 0-indexed
      console.log('Found search result:', searchResult)

      if (searchResult) {
        console.log('Search result page:', searchResult.page)
        console.log('Search result text:', searchResult.text?.substring(0, 100))
        console.log('Search result object:', searchResult)

        // Ensure we have a valid page number
        const targetPage = searchResult.page && searchResult.page > 0 ? searchResult.page : 1
        console.log('Using target page:', targetPage)

        // Set highlight data before loading PDF
        highlightText.value = searchResult.text || citation.snippet || ''
        highlightPage.value = targetPage

        console.log('Final highlight data:', {
          text: highlightText.value.substring(0, 100),
          page: highlightPage.value,
          searchResultPage: searchResult.page,
          targetPage: targetPage
        })

        // Load the PDF for this search result
        await loadDocumentForSource(searchResult)
        console.log('PDF loaded successfully for citation:', searchResult.document.title)
      } else {
        console.log('No corresponding search result found for citation index:', citation.index)
        console.log('Available search results:', currentMessage.searchResults.map((sr, idx) => ({ index: idx, page: sr.page })))
      }
    } else {
      console.log('No message with both citations and search results found')
      console.log('Available messages:', currentConversation.value?.messages.map((msg, idx) => ({
        index: idx,
        role: msg.role,
        hasCitations: !!msg.formattedCitations,
        hasSearchResults: !!msg.searchResults,
        citationsCount: msg.formattedCitations?.length || 0,
        searchResultsCount: msg.searchResults?.length || 0
      })))
    }
  } catch (error) {
    console.error('Error loading PDF for citation:', error)
    // Could show an error message to user
  }
}

// Helper functions for PDF loading (copied from WorkspaceDetailView)
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

const loadDocumentForSource = async (sourceData: any) => {
  try {
    // Try the base64 method first
    try {
      await loadDocumentViaBase64(sourceData)
    } catch (base64Error) {
      console.warn('Base64 method failed, trying download method:', base64Error)

      // Fallback to download method
      await loadDocumentViaDownload(sourceData)
    }
  } catch (error) {
    console.error('Error opening document:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
    alert(`Failed to open document: ${errorMessage}`)
  }
}

const loadDocumentViaBase64 = async (sourceData: any) => {
  // Fetch document as base64
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${apiBaseUrl}/api/v1/documents/${sourceData.document.id}/view`
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
  const pdfDocument = {
    id: sourceData.document.id,
    title: sourceData.document.title || sourceData.document.filename,
    filename: sourceData.document.filename,
    base64Data: bytes,
    mimetype: data.mimetype || 'application/pdf'
  }

  // Open in PDF viewer
  console.log('Opening PDF document:', pdfDocument)
  console.log('Source data page:', sourceData.page, 'text:', sourceData.text?.substring(0, 100))
  openPdf(pdfDocument)
}

const loadDocumentViaDownload = async (sourceData: any) => {
  // Fetch document as binary blob
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const url = `${apiBaseUrl}/api/v1/documents/${sourceData.document.id}/download`
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
  const pdfDocument = {
    id: sourceData.document.id,
    title: sourceData.document.title || sourceData.document.filename,
    filename: sourceData.document.filename,
    base64Data: bytes,
    mimetype: 'application/pdf'
  }

  // Open in PDF viewer
  openPdf(pdfDocument)
}

const handlePdfError = (error: string) => {
  console.error('PDF Viewer Error:', error)
  alert(`Failed to load PDF: ${error}`)
}

const handleClosePdfViewer = () => {
  closePdf()
  // Clear highlight data
  highlightText.value = ''
  highlightPage.value = 0
}

// const formatTime = (date: Date) => {
//   return new Intl.DateTimeFormat('en-US', {
//     hour: '2-digit',
//     minute: '2-digit'
//   }).format(date)
// }

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Watch for new messages and scroll to bottom
watch(() => currentConversation.value?.messages.length, () => {
  scrollToBottom()
  // Style Source links in new messages
  setTimeout(() => {
    styleSourceLinks()
  }, 100)
})

watch(isLoading, (loading) => {
  if (loading) {
    scrollToBottom()
  }
})

// Watch for conversation changes to restyle Source links
watch(() => currentConversation.value?.id, () => {
  setTimeout(() => {
    styleSourceLinks()
  }, 100)
})

const handleDocumentLinkClick = async (docIndex: number) => {
  console.log('Document link clicked:', docIndex)

  // Find the current message with search results
  const currentMessage = currentConversation.value?.messages.find(msg => msg.searchResults && msg.searchResults.length > 0)
  if (currentMessage && currentMessage.searchResults) {
    // Group results by document to find results for the specified docIndex
    const documentMap = new Map<string, any[]>()
    currentMessage.searchResults.forEach(result => {
      if (!documentMap.has(result.document.id)) {
        documentMap.set(result.document.id, [])
      }
      documentMap.get(result.document.id)!.push(result)
    })

    // Convert to array and find the document at the specified index
    const documentGroups = Array.from(documentMap.values())
    const targetGroup = documentGroups[docIndex - 1] // docIndex is 1-based

    if (targetGroup && targetGroup.length > 0) {
      const sourceData = targetGroup[0] // Use first result of the document
      console.log('Source data found for document:', docIndex, sourceData)

      try {
        // Set highlight data before loading PDF
        highlightText.value = sourceData.text || ''
        highlightPage.value = sourceData.page || 1
        console.log('Set highlight data:', { text: highlightText.value.substring(0, 100), page: highlightPage.value })

        // Try to load PDF using the same approach as WorkspaceDetailView
        await loadDocumentForSource(sourceData)
        console.log('PDF loaded successfully for source:', sourceData.document.title)
      } catch (error) {
        console.error('Error loading PDF for source:', error)
        // Could show an error message to user
      }
    } else {
      console.log('No results found for document index:', docIndex)
    }
  } else {
    console.log('No search results found in current conversation')
  }
}

// Global function for handling source link clicks
const handleGlobalSourceClick = (docIndex: number) => {
  console.log('Global source click:', docIndex)
  handleDocumentLinkClick(docIndex)
}

// Function to style Source links in message content
const styleSourceLinks = () => {
  nextTick(() => {
    // Find all message content elements
    const messageContents = document.querySelectorAll('.message__html-content')
    messageContents.forEach((content) => {
      // Find all text nodes and elements containing [docIndex, P. pages] pattern
      const walker = document.createTreeWalker(
        content,
        NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
        null
      )

      const nodesToProcess: Node[] = []
      let node = walker.nextNode()
      while (node) {
        if (node.nodeType === Node.TEXT_NODE) {
          if (node.textContent && /\[\d+,\s*P\.\s*[\d,\s]+\]/.test(node.textContent)) {
            nodesToProcess.push(node)
          }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          const element = node as Element
          if (element.textContent && /\[\d+,\s*P\.\s*[\d,\s]+\]/.test(element.textContent)) {
            nodesToProcess.push(node)
          }
        }
        node = walker.nextNode()
      }

      // Process found nodes
      nodesToProcess.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          const textNode = node as Text
          const text = textNode.textContent || ''
          const parent = textNode.parentElement

          if (parent && !parent.hasAttribute('onclick')) {
            // Split text and wrap [docIndex, P. pages] parts
            const parts = text.split(/(\[\d+,\s*P\.\s*[\d,\s]+\])/)

            if (parts.length > 1) {
              const fragment = document.createDocumentFragment()

              parts.forEach((part) => {
                if (/\[\d+,\s*P\.\s*[\d,\s]+\]/.test(part)) {
                  const docMatch = part.match(/\[(\d+),\s*P\.\s*[\d,\s]+\]/)
                  if (docMatch) {
                    const docIndex = parseInt(docMatch[1])
                    const linkElement = document.createElement('span')
                    linkElement.className = 'source-link'
                    linkElement.textContent = part
                    linkElement.onclick = () => handleGlobalSourceClick(docIndex)
                    fragment.appendChild(linkElement)
                  }
                } else if (part.trim()) {
                  fragment.appendChild(document.createTextNode(part))
                }
              })

              parent.replaceChild(fragment, textNode)
            }
          }
        }
      })
    })
  })
}

// Make it available globally
if (typeof window !== 'undefined') {
  (window as any).handleSourceClick = handleGlobalSourceClick
}

// Initialize
onMounted(async () => {
  await chatStore.fetchAvailableModels()
  scrollToBottom()
  // Style Source links after initial load
  setTimeout(() => {
    styleSourceLinks()
  }, 200)
})
</script>

<style scoped>
.chat-pane {
  display: flex;
  height: 100%;
  transition: all 0.3s ease;
}

.chat-pane--with-pdf {
  flex-direction: row;
}

.chat-pane__content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  transition: all 0.3s ease;
}

.chat-pane--with-pdf .chat-pane__content {
  flex: 1;
  max-width: calc(100% - 400px);
}

.chat-pane__pdf-panel {
  width: 50%;
  border-left: 1px solid var(--color-border);
  background-color: var(--color-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .chat-pane--with-pdf .chat-pane__content {
    max-width: calc(100% - 350px);
  }

  .chat-pane__pdf-panel {
    width: 350px;
  }
}

@media (max-width: 900px) {
  .chat-pane--with-pdf {
    flex-direction: column;
  }

  .chat-pane--with-pdf .chat-pane__content {
    max-width: 100%;
  }

  .chat-pane__pdf-panel {
    width: 100%;
    height: 60vh;
    border-left: none;
    border-top: 1px solid var(--color-border);
  }
}

.chat-pane__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  backdrop-filter: blur(10px);
}

.chat-pane__title h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.chat-pane__controls {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.workspace-selector-button {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background-color: var(--color-background);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.workspace-selector-button:hover {
  background-color: var(--color-background-secondary);
  border-color: var(--color-border-focus);
}

.workspace-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-text-muted);
}

.workspace-selector-button.active {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.workspace-selector-button.active .workspace-icon {
  color: var(--color-primary);
}

.domain-selector-button {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background-color: var(--color-background);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.domain-selector-button:hover {
  background-color: var(--color-background-secondary);
  border-color: var(--color-border-focus);
}

.domain-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-text-muted);
}

.domain-selector-button.active {
  background-color: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.domain-selector-button.active .domain-icon {
  color: var(--color-primary);
}

.model-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  background-color: var(--color-background);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  min-width: 200px;
}

.model-select:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.1);
}

.chat-pane__messages {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  overflow-y: auto;
  padding: 1rem;
}

.chat-pane__messages::-webkit-scrollbar {
  width: 6px;
}

.chat-pane__messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-pane__messages::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.chat-pane__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
}

.empty-state__icon {
  width: 5rem;
  height: 5rem;
  margin: 0 auto 1rem;
  opacity: 0.75;
}

.empty-state h3 {
  margin: 0 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.empty-state p {
  margin: 0;
  font-size: 0.875rem;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-height: 70vh;
  max-width: 60%;
  min-width: 40%;
}
.chat-pane--with-pdf .messages-list {
  height: 100%;
  max-width: 100%;
}

.message {
  display: flex;
  gap: 0.75rem;
}

.message__avatar {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-text-muted);
}

.avatar-icon-bot {
  width: 2rem;
  height: 2rem;
  background: none;
}

.message--user {
  display: flex;
  justify-content: right;
}

.message--user .message__content {
  min-width: 150px;
  padding: 0.5rem 1rem;
  border-radius: 15px 15px 0 15px;
  background-color: var(--overlay-lightest);
}

.message--user .avatar-icon {
  color: white;
}

.message__content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.context-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary);
  border-radius: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-primary);
}

.context-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.message__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.message__role {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.message__time {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.message__text {
  color: var(--color-text-primary);
  line-height: 1.6;
}

.message__plain-text {
  white-space: pre-wrap;
}


.message__html-content h1,
.message__html-content h2,
.message__html-content h3,
.message__html-content h4,
.message__html-content h5,
.message__html-content h6 {
  margin: 1rem 0 0.5rem;
  font-weight: 600;
}

.message__html-content p {
  margin: 0.5rem 0;
}

.message__html-content pre {
  background-color: var(--color-background-secondary);
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message__html-content code {
  background-color: var(--color-background-secondary);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.message__html-content pre code {
  background: none;
  padding: 0;
}

/* Citation numbers styling in message content */
.message__html-content {
  position: relative;
}

/* Make sure citation numbers are visible and clickable */
.message__html-content sup {
  color: var(--color-primary);
  font-weight: 600;
  cursor: pointer;
  background-color: var(--color-primary-light);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  margin-left: 0.125rem;
  transition: all 0.2s;
}

.message__html-content sup:hover {
  background-color: var(--color-primary);
  color: white;
  transform: scale(1.1);
}

/* Prevent all text from being clickable by default */
.message__html-content {
  user-select: text;
}

.message__html-content * {
  cursor: text !important;
}

/* Style for Source links specifically */
.message__html-content :deep([onclick*="handleSourceClick"]) {
  color: var(--color-primary) !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  background-color: var(--color-primary-light) !important;
  padding: 0.125rem 0.375rem !important;
  border-radius: 0.375rem !important;
  font-size: 0.875rem !important;
  margin: 0 0.125rem !important;
  transition: all 0.2s ease !important;
  text-decoration: none !important;
  border: 1px solid transparent !important;
  display: inline-block !important;
  user-select: none !important;
}

.message__html-content :deep([onclick*="handleSourceClick"]):hover {
  background-color: var(--color-primary) !important;
  color: white !important;
  transform: scale(1.05) !important;
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2) !important;
}

/* Style for dynamically added source-link class */
.message__html-content .source-link {
  color: var(--color-primary) !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  background-color: var(--color-primary-light) !important;
  padding: 0.125rem 0.375rem !important;
  border-radius: 0.375rem !important;
  font-size: 0.875rem !important;
  margin: 0 0.125rem !important;
  transition: all 0.2s ease !important;
  text-decoration: none !important;
  border: 1px solid transparent !important;
  display: inline-block !important;
  user-select: none !important;
}

.message__html-content .source-link:hover {
  background-color: var(--color-primary) !important;
  color: white !important;
  transform: scale(1.05) !important;
  box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2) !important;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.typing-indicator span {
  width: 0.5rem;
  height: 0.5rem;
  background-color: var(--color-text-muted);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

.chat-pane__input {
  padding: 1rem 1.5rem;
  backdrop-filter: blur(10px);
}

.mode-switcher {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  padding: 0.25rem;
  background-color: var(--color-background-secondary);
  border-radius: 0.75rem;
}

.mode-button {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-button:hover {
  background-color: var(--color-background);
}

.mode-button.active {
  border: 1px solid var(--color-primary);
  background-color: var(--color-primary-light);
  color: var(--color-primary);
}

.mode-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.mode-label {
  font-weight: 500;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 1rem;
  background-color: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 0.5rem;
  color: var(--color-error);
  font-size: 0.875rem;
}

.error-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.error-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--color-error);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
}

.error-dismiss:hover {
  background-color: rgba(220, 38, 38, 0.1);
}

.dismiss-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.input-form {
  width: 100%;
}

.input-container {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  min-height: 3.5rem;
  max-height: 8rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background-color: var(--color-background);
  color: var(--color-text-primary);
  font-size: 0.875rem;
  line-height: 1.4;
  resize: none;
  font-family: inherit;
}

.message-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.1);
}

.message-input::placeholder {
  color: var(--color-text-muted);
}

.send-button {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border: none;
  border-radius: 0.75rem;
  background-color: var(--color-primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.send-button:hover:not(:disabled) {
  background-color: var(--color-primary-hover);
}

.send-button:disabled {
  background-color: var(--color-text-muted);
  cursor: not-allowed;
}

.send-icon {
  width: 1rem;
  height: 1rem;
}

</style>