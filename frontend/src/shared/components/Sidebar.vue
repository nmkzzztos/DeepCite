<template>
  <aside class="sidebar" :class="{ 'sidebar--collapsed': isCollapsed }">
    <div class="sidebar__header">
      <!-- Logo -->
      <img src="/logo.svg" class="sidebar__header-logo" />

      <!-- Collapse Toggle -->
      <button 
        @click="toggleCollapse"
        class="collapse-toggle"
        :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <PanelLeftOpen class="collapse-icon" :class="{ 'collapse-icon--rotated': !isCollapsed }" />
      </button>

      <!-- Navigation Tabs -->
      <div class="nav-tabs" v-if="!isCollapsed">
        <button 
          @click="navigateToSection('chat')"
          class="nav-tab"
          :class="{ 'nav-tab--active': activeSection === 'chat' }"
        >
          <MessageSquare class="nav-tab-icon" />
          Chat
        </button>
        <button 
          @click="navigateToSection('workspaces')"
          class="nav-tab"
          :class="{ 'nav-tab--active': activeSection === 'workspaces' }"
        >
          <FolderOpen class="nav-tab-icon" />
          Workspaces
        </button>
        <button 
          @click="navigateToSection('papers')"
          class="nav-tab"
          :class="{ 'nav-tab--active': activeSection === 'papers' }"
        >
        <FileSearch2 class="nav-tab-icon" />
          Search Papers
        </button>
      </div>

      <!-- Collapsed Navigation Icons -->
      <div class="nav-icons" v-else>
        <button 
          @click="navigateToSection('chat')"
          class="nav-icon"
          :class="{ 'nav-icon--active': activeSection === 'chat' }"
          :title="'Chat'"
        >
          <MessageSquare class="nav-icon-svg" />
        </button>
        <button 
          @click="navigateToSection('workspaces')"
          class="nav-icon"
          :class="{ 'nav-icon--active': activeSection === 'workspaces' }"
          :title="'Workspaces'"
        >
          <FolderOpen class="nav-icon-svg" />
        </button>
        <button 
          @click="navigateToSection('papers')"
          class="nav-icon"
          :class="{ 'nav-icon--active': activeSection === 'papers' }"
          :title="'Papers'"
        >
          <FileSearch2 class="nav-icon-svg" />
        </button>
      </div>

    </div>

    <nav class="sidebar__nav" v-if="!isCollapsed">
      <!-- Chat Section -->
      <div v-if="activeSection === 'chat' || activeSection === 'papers'" class="nav-section">
        <!-- Mode Tabs for Chat Section -->
        <div class="mode-tabs">
          <button 
            @click="switchChatMode('normal')"
            class="mode-tab"
            :class="{ 'mode-tab--active': chatMode === 'normal' }"
            :title="'Normal Chat'"
          >
            <MessageSquare class="mode-tab-icon" />
            <span>Chat</span>
          </button>
          <button 
            @click="switchChatMode('workspaces')"
            class="mode-tab"
            :class="{ 'mode-tab--active': chatMode === 'workspaces' }"
            :title="'Chat with Documents'"
          >
            <Database class="mode-tab-icon" />
            <span>Docs</span>
          </button>
          <button 
            @click="switchChatMode('internet')"
            class="mode-tab"
            :class="{ 'mode-tab--active': chatMode === 'internet' }"
            :title="'Internet Search'"
          >
            <Globe class="mode-tab-icon" />
            <span>Web</span>
          </button>
        </div>

        <h3 class="nav-section__title">
          {{ getModeTitle(chatMode) }} 
          <span class="conversation-count">({{ currentModeConversations.length }})</span>
        </h3>
        
        <div v-if="currentModeConversations.length === 0" class="nav-section__empty">
          <MessageSquare class="empty-icon" />
          <p>{{ getModeEmptyMessage(chatMode) }}</p>
        </div>
        
        <div v-else class="conversations-list">
          <div
            v-for="conversation in currentModeConversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{ 'conversation-item--active': conversation.id === currentConversationId }"
            @click="handleChatSelected(conversation.id)"
          >
            <div class="conversation-item__content">
              <div class="conversation-item__title">{{ conversation.title }}</div>
              <div class="conversation-item__meta">
                <span class="conversation-item__mode">
                  <component 
                    :is="getModeIcon(conversation.chatMode || null)" 
                    class="mode-indicator-icon"
                  />
                  {{ getModelName(conversation) }}
                </span>
                <span class="conversation-item__time">{{ formatRelativeTime(conversation.updatedAt) }}</span>
              </div>
            </div>
            
            <button 
              @click.stop="handleChatDeleted(conversation.id)"
              class="conversation-item__delete"
              :title="'Delete conversation'"
            >
              <Trash2 class="delete-icon" />
            </button>
          </div>
        </div>
      </div>

      <!-- Workspaces Section -->
      <div v-else class="nav-section">
        <h3 class="nav-section__title">Workspaces</h3>
        
        <div v-if="workspaces.length === 0" class="nav-section__empty">
          <FolderOpen class="empty-icon" />
          <p>No workspaces yet</p>
        </div>
        
        <div v-else class="workspaces-list">
          <div
            v-for="workspace in workspaces"
            :key="workspace.id"
            class="workspace-item"
            :class="{ 'workspace-item--active': workspace.id === currentWorkspaceId }"
            @click="handleWorkspaceSelected(workspace.id)"
          >
            <div class="workspace-item__content">
              <div class="workspace-item__title">{{ workspace.name }}</div>
              <div class="workspace-item__meta">
                <span class="workspace-item__docs">{{ workspace.documentCount || 0 }} docs</span>
                <span class="workspace-item__time">{{ formatRelativeTime(workspace.updatedAt) }}</span>
              </div>
            </div>
            
            <button 
              @click.stop="handleWorkspaceDeleted(workspace.id)"
              class="workspace-item__delete"
              :title="'Delete workspace'"
            >
              <Trash2 class="delete-icon" />
            </button>
          </div>
        </div>
      </div>
    </nav>
    <div class="sidebar__footer">
      <img src="/logo_with_name.svg" class="sidebar__footer-logo" />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MessageSquare, Trash2, Database, PanelLeftOpen, Globe, FolderOpen, FileSearch2 } from 'lucide-vue-next'
import { useChat } from '@/features/chat'
import { useWorkspace } from '@/features/workspaces'
import type { NavigationSection } from '@/shared/types'
import type { ChatMode } from '@/features/chat/stores/chatStore'

// Define emits
const emit = defineEmits<{
  'chat-selected': [chatId: string]
  'chat-deleted': [chatId: string]
  'workspace-selected': [workspaceId: string]
  'new-workspace': []
  'workspace-deleted': [workspaceId: string]
  'section-changed': [section: NavigationSection]
}>()

const router = useRouter()

// Active section state
const activeSection = ref<NavigationSection>('chat')

// Collapse state
const isCollapsed = ref(false)

// Use chat composable
const {
  currentConversation,
  currentModeConversations,
  chatMode,
  availableModels,
  selectChat,
  deleteChat,
  createNewChat,
  setChatMode
} = useChat()

// Use workspace composable
const {
  workspaces,
  currentWorkspaceId,
  fetchWorkspaces,
  selectWorkspace,
  deleteWorkspace
} = useWorkspace()

// Computed properties
const currentConversationId = computed(() => currentConversation.value?.id || null)

// Methods
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const switchChatMode = (mode: ChatMode) => {
  setChatMode(mode)
}

const getModeTitle = (mode: ChatMode | null): string => {
  switch (mode) {
    case 'normal':
      return 'Chat Conversations'
    case 'workspaces':
      return 'Document Chats'
    case 'internet':
      return 'Web Search Chats'
    case null:
      return 'Chat Conversations'
    default:
      return 'Conversations'
  }
}

const getModeEmptyMessage = (mode: ChatMode | null): string => {
  switch (mode) {
    case 'normal':
      return 'No chat conversations yet'
    case 'workspaces':
      return 'No document chats yet'
    case 'internet':
      return 'No web search chats yet'
    case null:
      return 'No chat conversations yet'
    default:
      return 'No conversations yet'
  }
}

const getModeIcon = (mode: ChatMode | null) => {
  switch (mode) {
    case 'normal':
      return MessageSquare
    case 'workspaces':
      return Database
    case 'internet':
      return Globe
    case null:
      return MessageSquare
    default:
      return MessageSquare
  }
}


const handleChatSelected = (chatId: string) => {
  selectChat(chatId)
  emit('chat-selected', chatId)
  router.push('/')
}

const handleChatDeleted = (chatId: string) => {
  deleteChat(chatId)
  emit('chat-deleted', chatId)
}


const handleWorkspaceSelected = (workspaceId: string) => {
  selectWorkspace(workspaceId)
  emit('workspace-selected', workspaceId)
  router.push(`/workspace/${workspaceId}`)
}

const handleWorkspaceDeleted = async (workspaceId: string) => {
  if (confirm('Are you sure you want to delete this workspace? This action cannot be undone.')) {
    try {
      await deleteWorkspace(workspaceId)
      emit('workspace-deleted', workspaceId)
    } catch (error) {
      console.error('Failed to delete workspace:', error)
    }
  }
}

const getModelName = (conversation: any) => {
  // For workspaces mode, show workspace name instead of model
  if (conversation.chatMode === 'workspaces' && conversation.selectedWorkspaces?.length > 0) {
    const workspaceId = conversation.selectedWorkspaces[0]
    const workspace = workspaces.value.find(w => w.id === workspaceId)
    if (workspace) {
      return workspace.name.length > 15 ? workspace.name.substring(0, 15) + '...' : workspace.name
    }
  }

  // For other modes, show model name
  const model = availableModels.value.find(m => m.id === conversation.modelId)
  return model ? model.name : conversation.modelId
}

const navigateToSection = (section: NavigationSection) => {
  activeSection.value = section
  emit('section-changed', section)

  if (section === 'workspaces') {
    router.push('/workspaces')
  } else if (section === 'papers') {
    router.push('/papers')
  } else {
    // Check if we already have an active temporary chat
    if (currentConversation.value && currentConversation.value.isTemporary) {
      // Use existing temporary chat
      router.push('/')
      emit('chat-selected', currentConversation.value.id)
    } else {
      // Create a new temporary chat for regular chat section
      router.push('/')
      const chatId = createNewChat(undefined, true) // Create temporary chat
      emit('chat-selected', chatId)
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

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return targetDate.toLocaleDateString()
}

// Watch for section changes and update active section based on route
watch(() => router.currentRoute.value.path, (newPath) => {
  if (newPath.startsWith('/workspace') || newPath === '/workspaces') {
    activeSection.value = 'workspaces'
  } else if (newPath.startsWith('/papers')) {
    activeSection.value = 'papers'
  } else {
    activeSection.value = 'chat'
    // Check if we already have an active temporary chat
    if (currentConversation.value && currentConversation.value.isTemporary) {
      // Use existing temporary chat
      emit('chat-selected', currentConversation.value.id)
    } else {
      // Create a new temporary chat for regular chat route
      const chatId = createNewChat(undefined, true) // Create temporary chat
      emit('chat-selected', chatId)
    }
  }
}, { immediate: true })

// Initialize on mount
onMounted(() => {
  // Initialize workspaces
  fetchWorkspaces()
})
</script>

<style scoped>
.sidebar {
  width: 250px;
  height: 100vh;
  background-color: var(--color-surface);
  border-right: 1px solid var(--color-border-light);
  border-radius: 0 10px 10px 0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.sidebar--collapsed {
  width: 60px;
  height: 200px;
  border: 1px solid #e5e7eb;
  border-radius: 0 0 25px 0;
}

.sidebar__header {
  padding: 1rem 1rem 0 1rem;
}

.sidebar__header-logo {
  display: none;
  position: absolute;
  left: 125px;
  width: 25px;
  height: 25px;
}

.sidebar--collapsed .sidebar__header-logo {
  display: none;
}

.sidebar--collapsed .sidebar__header {
  padding: 0.75rem 0.5rem;
}

.sidebar--collapsed .sidebar__footer {
  display: none;
}

.collapse-toggle {
  position: relative;
  right: -90%;
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 0.25rem;
  margin-bottom: 10px;
  border-radius: 0.25rem;
  transition: all 0.2s;
  z-index: 10;
}

.sidebar--collapsed .collapse-toggle {
  position: relative;
  right: -20%;
  margin-bottom: 1rem;
  align-self: center;
}

.collapse-toggle:hover {
  background-color: var(--color-background-tertiary);
  color: var(--color-text-primary);
}

.collapse-icon {
  width: 1rem;
  height: 1rem;
  transition: transform 0.3s ease;
}

.collapse-icon--rotated {
  transform: rotate(180deg);
}

.nav-tabs {
  display: flex;
  flex-direction: column;
  background-color: var(--color-background-tertiary);
  border-radius: 0.5rem;
  padding: 0.25rem;
  margin-bottom: 1rem;
}

.nav-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: left;
  gap: 0.5rem;
  padding: 0.5rem;
  background: none;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-tab:hover {
  color: var(--color-text-primary);
}

.nav-tab--active {
  background-color: white;
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.nav-tab-icon {
  width: 1rem;
  height: 1rem;
}

.nav-icons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  background: none;
  border: none;
  border-radius: 0.5rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-icon:hover {
  background-color: var(--color-background-tertiary);
  color: var(--color-text-primary);
}

.nav-icon--active {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
}

.nav-icon-svg {
  width: 1.25rem;
  height: 1.25rem;
}

.action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  margin-bottom: 1rem;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.action-button:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
  transform: translateY(-2px);
  color: var(--color-primary);
}

.action-icon {
  width: 1rem;
  height: 1rem;
}

.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  padding: 0 0 1rem 0;
}

.sidebar__nav::-webkit-scrollbar {
  width: 6px;
}

.sidebar__nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar__nav::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.sidebar__nav::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.nav-section {
  padding: 0 1rem;
}

.mode-tabs {
  display: flex;
  background-color: var(--color-background-tertiary);
  border-radius: 0.5rem;
  padding: 0.25rem;
  margin-bottom: 1rem;
}

.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.375rem 0.5rem;
  background: none;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab:hover {
  color: var(--color-text-primary);
}

.mode-tab--active {
  background-color: white;
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.mode-tab-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.nav-section__title {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.05em;
}

.conversation-count {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--color-text-muted);
  opacity: 0.8;
}

.nav-section__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-text-muted);
}

.empty-icon {
  width: 2rem;
  height: 2rem;
  margin-bottom: 0.5rem;
  opacity: 0.5;
}

.nav-section__empty p {
  margin: 0;
  font-size: 0.875rem;
}

.conversations-list,
.workspaces-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.conversation-item,
.workspace-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.conversation-item:hover,
.workspace-item:hover {
  background-color: var(--color-background-tertiary);
}

.conversation-item--active,
.workspace-item--active {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
}

.conversation-item__content,
.workspace-item__content {
  flex: 1;
  min-width: 0;
}

.conversation-item__title,
.workspace-item__title {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--color-text-primary);
  margin-bottom: 0.25rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-item--active .conversation-item__title,
.workspace-item--active .workspace-item__title {
  color: var(--color-primary);
}

.conversation-item__meta,
.workspace-item__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.conversation-item__model,
.workspace-item__docs {
  font-weight: 500;
}

.conversation-item__mode {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
}

.mode-indicator-icon {
  width: 0.75rem;
  height: 0.75rem;
  opacity: 0.7;
}

.conversation-item__time,
.workspace-item__time {
  opacity: 0.8;
}

.conversation-item__delete,
.workspace-item__delete {
  opacity: 0;
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: opacity 0.2s, background-color 0.2s;
}

.conversation-item:hover .conversation-item__delete,
.workspace-item:hover .workspace-item__delete {
  opacity: 1;
}

.conversation-item__delete:hover,
.workspace-item__delete:hover {
  background-color: rgba(220, 38, 38, 0.1);
  color: var(--color-error);
}

.delete-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.sidebar__footer {
  display: flex;
  justify-content: center;
  min-height: 75px;
}

.sidebar__footer-logo {
  max-width: 75px;
  opacity: 0.75;
}
</style>