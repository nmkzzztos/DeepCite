<template>
  <div id="app" class="app">
    <Sidebar 
      @chat-selected="handleChatSelected"
      @new-chat="handleNewChat"
      @chat-deleted="handleChatDeleted"
      @workspace-selected="handleWorkspaceSelected"
      @new-workspace="handleNewWorkspace"
      @workspace-deleted="handleWorkspaceDeleted"
      @section-changed="handleSectionChanged"
    />
    
    <main class="app__main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/Sidebar.vue'
import type { NavigationSection } from '@/shared/types'

const handleChatSelected = (chatId: string) => {
  console.log('Chat selected:', chatId)
}

const handleNewChat = () => {
  console.log('New chat created')
}

const handleChatDeleted = (chatId: string) => {
  console.log('Chat deleted:', chatId)
}

const handleWorkspaceSelected = (workspaceId: string) => {
  console.log('Workspace selected:', workspaceId)
}

const handleNewWorkspace = () => {
  console.log('New workspace requested')
}

const handleWorkspaceDeleted = (workspaceId: string) => {
  console.log('Workspace deleted:', workspaceId)
}

const handleSectionChanged = (section: NavigationSection) => {
  console.log('Section changed to:', section)
}
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background-color: var(--color-background-secondary);
}

.app__main {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
</style>