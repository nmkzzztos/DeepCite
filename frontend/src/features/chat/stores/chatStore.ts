import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  htmlContent?: string
  timestamp: Date
  model?: string
  searchResults?: Array<{
    paragraph_id: string
    text: string
    score: number
    page?: number
    section_path?: string
    document: {
      id: string
      title: string
      filename: string
      authors?: string[]
      year?: number
    }
  }>
  formattedCitations?: Array<{
    index: number
    title: string
    url: string
    date: string
    snippet: string
    last_updated: string
  }>
  citations?: string[]
  contextUsed?: boolean
}

export type ChatMode = 'normal' | 'workspaces' | 'internet'

export interface ChatConversation {
  id: string
  title: string
  messages: ChatMessage[]
  modelId: string
  createdAt: Date
  updatedAt: Date
  selectedWorkspaces?: string[]
  selectedDocuments?: Record<string, string[]>
  chatMode?: ChatMode | null
  chatModeLocked?: boolean
  selectedDomains?: string[]
  isTemporary?: boolean
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  description: string
  max_completion_tokens?: number
  supports_streaming: boolean
}

export const useChatStore = defineStore('chat', () => {
  // State
  const conversations = ref<ChatConversation[]>([])
  const currentConversationId = ref<string | null>(null)
  const availableModels = ref<ModelInfo[]>([])
  const selectedModelId = ref<string>('gpt-5')
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const chatMode = ref<ChatMode | null>('normal')
  const selectedDomains = ref<string[]>([])

  // Computed
  const currentConversation = computed(() => {
    if (!currentConversationId.value) return null
    return conversations.value.find(c => c.id === currentConversationId.value) || null
  })

  const sortedConversations = computed(() => {
    return [...conversations.value].sort((a, b) =>
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  })

  // Conversations for display (excluding temporary ones)
  const displayConversations = computed(() => {
    return sortedConversations.value.filter(conv => !conv.isTemporary)
  })

  // Conversations filtered by chat mode
  const conversationsByMode = computed(() => {
    const byMode: Record<ChatMode | 'unassigned', ChatConversation[]> = {
      normal: [],
      workspaces: [],
      internet: [],
      unassigned: []
    }

    displayConversations.value.forEach(conv => {
      const mode = conv.chatMode ?? 'unassigned'
      byMode[mode].push(conv)
    })

    return byMode
  })

  // Conversations for current mode
  const currentModeConversations = computed(() => {
    const mode = chatMode.value || 'unassigned'
    return conversationsByMode.value[mode] || []
  })

  // Helper functions
  const getModeDisplayName = (mode: ChatMode | 'unassigned'): string => {
    switch (mode) {
      case 'normal':
        return 'New Chat'
      case 'workspaces':
        return 'New Workspace Chat'
      case 'internet':
        return 'New Internet Search'
      case 'unassigned':
        return 'New Chat'
      default:
        return 'New Chat'
    }
  }

  // Actions
  const loadFromLocalStorage = () => {
    try {
      const stored = localStorage.getItem('deepcite-conversations')
      if (stored) {
        const parsed = JSON.parse(stored)
        conversations.value = parsed.map((conv: any) => ({
          ...conv,
          createdAt: new Date(conv.createdAt),
          updatedAt: new Date(conv.updatedAt),
          messages: conv.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }))
      }

      const storedModelId = localStorage.getItem('deepcite-selected-model')
      if (storedModelId) {
        selectedModelId.value = storedModelId
      }

      // Don't restore current conversation on chat view - always create new one
      // const storedCurrentId = localStorage.getItem('deepcite-current-conversation')
      // if (storedCurrentId && conversations.value.find(c => c.id === storedCurrentId)) {
      //   currentConversationId.value = storedCurrentId
      // }

      const storedChatMode = localStorage.getItem('deepcite-chat-mode') as ChatMode
      if (storedChatMode && ['normal', 'workspaces', 'internet'].includes(storedChatMode)) {
        // Don't load global chat mode if current conversation has locked mode
        const currentConv = conversations.value.find(c => c.id === currentConversationId.value)
        if (!currentConv || !currentConv.chatModeLocked) {
          chatMode.value = storedChatMode
        }
      } else {
        // If no stored mode, set to normal
        chatMode.value = 'normal'
      }

      const storedDomains = localStorage.getItem('deepcite-selected-domains')
      if (storedDomains) {
        try {
          selectedDomains.value = JSON.parse(storedDomains)
        } catch (e) {
          console.error('Failed to parse stored domains:', e)
        }
      }
    } catch (e) {
      console.error('Failed to load from localStorage:', e)
    }
  }

  const saveToLocalStorage = () => {
    try {
      // Only save non-temporary conversations
      const permanentConversations = conversations.value.filter(conv => !conv.isTemporary)
      localStorage.setItem('deepcite-conversations', JSON.stringify(permanentConversations))
      localStorage.setItem('deepcite-selected-model', selectedModelId.value)

      // Only save current conversation ID if it's not temporary
      if (currentConversationId.value) {
        const currentConv = conversations.value.find(c => c.id === currentConversationId.value)
        if (currentConv && !currentConv.isTemporary) {
          localStorage.setItem('deepcite-current-conversation', currentConversationId.value)
        }
      }
    } catch (e) {
      console.error('Failed to save to localStorage:', e)
    }
  }

  const fetchAvailableModels = async () => {
    try {
      const response = await api.get('/chat/models')
      if (response.data.success) {
        availableModels.value = response.data.models
      }
    } catch (e) {
      console.error('Failed to fetch models:', e)
      error.value = 'Failed to load available models'
    }
  }

  const createNewConversation = (title?: string, isTemporary: boolean = false): string => {
    const id = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const conversation: ChatConversation = {
      id,
      title: title || 'New Chat',
      messages: [],
      modelId: selectedModelId.value,
      chatMode: null,
      chatModeLocked: false,
      selectedDomains: [...selectedDomains.value],
      createdAt: new Date(),
      updatedAt: new Date(),
      isTemporary
    }

    // If creating a temporary conversation, clean up old empty temporary conversations
    if (isTemporary) {
      conversations.value = conversations.value.filter(conv =>
        !conv.isTemporary || conv.messages.length > 0 || conv.id === currentConversationId.value
      )
    }

    conversations.value.push(conversation)
    currentConversationId.value = id

    // Only save to localStorage if not temporary
    if (!isTemporary) {
      saveToLocalStorage()
    }

    return id
  }

  const selectConversation = (id: string) => {
    const conversation = conversations.value.find(c => c.id === id)
    if (conversation) {
      currentConversationId.value = id
      selectedModelId.value = conversation.modelId
      selectedDomains.value = conversation.selectedDomains || []
      // Don't save temporary conversations to localStorage
      if (!conversation.isTemporary) {
        saveToLocalStorage()
      }
    }
  }

  const deleteConversation = (id: string) => {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index !== -1) {
      const deletedConversation = conversations.value[index]
      conversations.value.splice(index, 1)

      if (currentConversationId.value === id) {
        currentConversationId.value = conversations.value.length > 0 ? conversations.value[0].id : null
      }

      // Don't save to localStorage if we deleted a temporary conversation
      if (!deletedConversation.isTemporary) {
        saveToLocalStorage()
      }
    }
  }

  const updateConversationTitle = (id: string, title: string) => {
    const conversation = conversations.value.find(c => c.id === id)
    if (conversation) {
      conversation.title = title
      conversation.updatedAt = new Date()
      // Don't save temporary conversations to localStorage
      if (!conversation.isTemporary) {
        saveToLocalStorage()
      }
    }
  }

  const setSelectedModel = (modelId: string) => {
    selectedModelId.value = modelId

    // Update current conversation's model
    if (currentConversation.value) {
      currentConversation.value.modelId = modelId
      currentConversation.value.updatedAt = new Date()
      // Don't save temporary conversations to localStorage
      if (!currentConversation.value.isTemporary) {
        saveToLocalStorage()
      }
    } else {
      // Save global model selection even without current conversation
      localStorage.setItem('deepcite-selected-model', modelId)
    }
  }

  const setWorkspaceSelection = (workspaces: string[], documents: Record<string, string[]>) => {
    if (currentConversation.value) {
      currentConversation.value.selectedWorkspaces = workspaces
      currentConversation.value.selectedDocuments = documents
      currentConversation.value.updatedAt = new Date()
      // Don't save temporary conversations to localStorage
      if (!currentConversation.value.isTemporary) {
        saveToLocalStorage()
      }
    }
  }

  const setChatMode = (mode: ChatMode | null) => {
    chatMode.value = mode

    // Save mode to localStorage (only if current conversation's mode is not locked)
    if (mode && (!currentConversation.value || !currentConversation.value.chatModeLocked)) {
      localStorage.setItem('deepcite-chat-mode', mode)
    }

    // Auto-select appropriate model for the mode
    if (mode === 'internet') {
      // Try to select a Perplexity model if available
      const perplexityModels = availableModels.value.filter(m => m.provider === 'perplexity')
      if (perplexityModels.length > 0) {
        // Prefer sonar model, fallback to first available
        const sonarModel = perplexityModels.find(m => m.id === 'sonar') || perplexityModels[0]
        setSelectedModel(sonarModel.id)
      }
    }
  }

  const setSelectedDomains = (domains: string[]) => {
    selectedDomains.value = domains

    // Update current conversation's domains
    if (currentConversation.value) {
      currentConversation.value.selectedDomains = domains
      currentConversation.value.updatedAt = new Date()
      // Don't save temporary conversations to localStorage
      if (!currentConversation.value.isTemporary) {
        saveToLocalStorage()
      }
    }

    // Save domains to localStorage
    localStorage.setItem('deepcite-selected-domains', JSON.stringify(domains))
  }

  // Track active requests to prevent race conditions
  const activeRequests = ref<Set<string>>(new Set())
  const requestQueue = ref<Map<string, AbortController>>(new Map())

  const sendMessage = async (content: string): Promise<void> => {
    if (!currentConversationId.value) {
      createNewConversation()
    }

    const conversation = currentConversation.value
    if (!conversation) return

    // Generate unique request ID
    const requestId = `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    
    // Cancel any existing request for this conversation
    const existingController = requestQueue.value.get(conversation.id)
    if (existingController) {
      existingController.abort()
      requestQueue.value.delete(conversation.id)
    }

    // Create new abort controller for this request
    const abortController = new AbortController()
    requestQueue.value.set(conversation.id, abortController)
    activeRequests.value.add(requestId)

    // Add user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content,
      timestamp: new Date()
    }
    
    conversation.messages.push(userMessage)
    conversation.updatedAt = new Date()

    // Update title if this is the first message
    if (conversation.messages.length === 1) {
      const title = content.length > 50 ? content.slice(0, 50) + '...' : content
      conversation.title = title

      // Update conversation mode to current global mode and lock it
      conversation.chatMode = chatMode.value
      conversation.chatModeLocked = true

      // Convert temporary conversation to permanent when first message is sent
      if (conversation.isTemporary) {
        conversation.isTemporary = false
        // Save to localStorage now that it's permanent
        saveToLocalStorage()
      }
    }

    // Add placeholder assistant message
    const placeholderMessage: ChatMessage = {
      id: `msg-${Date.now()}-assistant-placeholder`,
      role: 'assistant',
      content: '...',
      timestamp: new Date()
    }
    conversation.messages.push(placeholderMessage)

    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/chat/send', {
        message: content,
        model_id: selectedModelId.value,
        request_id: requestId,
        conversation_history: conversation.messages.slice(0, -2).map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        chat_mode: chatMode.value,
        selected_workspaces: conversation.selectedWorkspaces || [],
        selected_documents: conversation.selectedDocuments || {},
        selected_domains: selectedDomains.value
      }, {
        signal: abortController.signal,
        timeout: 120000 // 2 minute timeout
      })

      // Check if this request is still active (not cancelled)
      if (!activeRequests.value.has(requestId)) {
        return // Request was cancelled
      }

      if (response.data.success) {
        // Remove placeholder message
        const placeholderIndex = conversation.messages.findIndex(msg => msg.id === placeholderMessage.id)
        if (placeholderIndex !== -1) {
          conversation.messages.splice(placeholderIndex, 1)
        }

        const assistantMessage: ChatMessage = {
          id: `msg-${Date.now()}-assistant`,
          role: 'assistant',
          content: response.data.response.content,
          htmlContent: response.data.response.html_content,
          timestamp: new Date(response.data.response.timestamp),
          model: response.data.response.model,
          searchResults: response.data.response.search_results || [],
          formattedCitations: response.data.response.formatted_citations || [],
          citations: response.data.response.citations || [],
          contextUsed: response.data.response.context_used || false
        }
        
        conversation.messages.push(assistantMessage)
        conversation.updatedAt = new Date()
      } else {
        throw new Error(response.data.error || 'Failed to send message')
      }
    } catch (e: any) {
      // Remove placeholder message on error
      const placeholderIndex = conversation.messages.findIndex(msg => msg.id === placeholderMessage.id)
      if (placeholderIndex !== -1) {
        conversation.messages.splice(placeholderIndex, 1)
      }

      if (e.name === 'AbortError' || e.code === 'ECONNABORTED') {
        console.log('Request was cancelled')
        return // Don't show error for cancelled requests
      }

      error.value = e.response?.data?.error || e.message || 'Failed to send message'
      console.error('Failed to send message:', e)
    } finally {
      activeRequests.value.delete(requestId)
      requestQueue.value.delete(conversation.id)
      isLoading.value = false
      // Don't save temporary conversations to localStorage
      if (!conversation.isTemporary) {
        saveToLocalStorage()
      }
    }
  }

  const cancelActiveRequests = () => {
    requestQueue.value.forEach((controller) => {
      controller.abort()
    })
    requestQueue.value.clear()
    activeRequests.value.clear()
    isLoading.value = false
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // State
    conversations,
    currentConversationId,
    availableModels,
    selectedModelId,
    isLoading,
    error,
    activeRequests,
    chatMode,
    selectedDomains,

    // Computed
    currentConversation,
    sortedConversations,
    displayConversations,
    conversationsByMode,
    currentModeConversations,

    // Actions
    loadFromLocalStorage,
    fetchAvailableModels,
    createNewConversation,
    selectConversation,
    deleteConversation,
    updateConversationTitle,
    setSelectedModel,
    sendMessage,
    cancelActiveRequests,
    clearError,
    setWorkspaceSelection,
    setChatMode,
    setSelectedDomains
  }
})