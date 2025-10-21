<template>
  <div class="chat-view">
    <ChatPane />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ChatPane from '../components/ChatPane.vue'
import { useChatStore } from '../stores/chatStore'

const chatStore = useChatStore()

onMounted(() => {
  // Load conversations from localStorage
  chatStore.loadFromLocalStorage()

  // Create a new temporary conversation if there's no current conversation or it's not temporary
  // This ensures a fresh temporary chat when returning to chat from other views
  if (!chatStore.currentConversation || !chatStore.currentConversation.isTemporary) {
    chatStore.createNewConversation(undefined, true) // Create temporary chat
  }
})
</script>

<style scoped>
.chat-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>