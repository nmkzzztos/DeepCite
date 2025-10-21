import { computed } from 'vue'
import { useChatStore } from '../stores/chatStore'

export function useChat() {
  const chatStore = useChatStore()

  const currentConversation = computed(() => chatStore.currentConversation)
  const conversations = computed(() => chatStore.displayConversations)
  const currentModeConversations = computed(() => chatStore.currentModeConversations)
  const conversationsByMode = computed(() => chatStore.conversationsByMode)
  const chatMode = computed(() => chatStore.chatMode)
  const availableModels = computed(() => chatStore.availableModels)
  const selectedModelId = computed(() => chatStore.selectedModelId)
  const isLoading = computed(() => chatStore.isLoading)
  const error = computed(() => chatStore.error)

  const createNewChat = (title?: string, isTemporary: boolean = false) => {
    return chatStore.createNewConversation(title, isTemporary)
  }

  const selectChat = (id: string) => {
    chatStore.selectConversation(id)
  }

  const deleteChat = (id: string) => {
    chatStore.deleteConversation(id)
  }

  const sendMessage = async (content: string) => {
    await chatStore.sendMessage(content)
  }

  const setModel = (modelId: string) => {
    chatStore.setSelectedModel(modelId)
  }

  const clearError = () => {
    chatStore.clearError()
  }

  const cancelRequests = () => {
    chatStore.cancelActiveRequests()
  }

  const hasActiveRequests = computed(() => chatStore.activeRequests.size > 0)

  const setWorkspaceSelection = (workspaces: string[], documents: Record<string, string[]>) => {
    chatStore.setWorkspaceSelection(workspaces, documents)
  }

  const setChatMode = (mode: string) => {
    chatStore.setChatMode(mode as any)
  }

  return {
    // State
    currentConversation,
    conversations,
    currentModeConversations,
    conversationsByMode,
    chatMode,
    availableModels,
    selectedModelId,
    isLoading,
    error,
    hasActiveRequests,

    // Actions
    createNewChat,
    selectChat,
    deleteChat,
    sendMessage,
    setModel,
    cancelRequests,
    clearError,
    setWorkspaceSelection,
    setChatMode
  }
}