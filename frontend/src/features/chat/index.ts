// Chat feature exports
export { default as ChatPane } from './components/ChatPane.vue'
export { default as ChatView } from './views/ChatView.vue'
export { useChatStore } from './stores/chatStore'
export { useChat } from './composables/useChat'

export type { ChatMessage, ChatConversation, ModelInfo } from './stores/chatStore'