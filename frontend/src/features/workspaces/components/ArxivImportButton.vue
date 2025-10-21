<template>
  <button 
    @click="navigateToArxivImport"
    class="arxiv-import-button"
    :title="'Import papers from arXiv'"
  >
    <BookOpen class="button-icon" />
    Import from arXiv
  </button>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { BookOpen } from 'lucide-vue-next'

interface Props {
  workspaceId: string
}

const props = defineProps<Props>()
const router = useRouter()

const navigateToArxivImport = () => {
  router.push(`/workspace/${props.workspaceId}/arxiv`)
}
</script>

<style scoped>
.arxiv-import-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.arxiv-import-button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
}

.button-icon {
  width: 16px;
  height: 16px;
}
</style>