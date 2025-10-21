<template>
  <div class="min-h-screen from-slate-50 to-white px-6 py-8">
    <div class="max-w-7xl mx-auto">
      <!-- Header Section -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-12">
        <div class="mb-6 sm:mb-0">
          <h1 class="text-3xl font-light text-slate-800 tracking-tight">Import Papers from arXiv</h1>
          <p class="mt-2 text-slate-600 text-lg font-light">
            Search and import academic papers directly from arXiv
          </p>
        </div>
      </div>

      <!-- Search Component -->
      <PapersSearch
        :workspace-id="workspaceId"
        :show-workspace-selector="!workspaceId"
        @paper-imported="handlePaperImported"
      />

      <!-- Recent Imports -->
      <div v-if="recentImports.length > 0" class="mt-12">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center">
            <FileText class="w-4 h-4 text-slate-600" />
          </div>
          <h3 class="text-xl font-medium text-slate-800">Recently Imported</h3>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="importItem in recentImports"
            :key="importItem.paper.id"
            class="group bg-white border border-slate-200 rounded-xl p-6 hover:border-slate-300 hover:shadow-lg transition-all duration-200 cursor-pointer relative overflow-hidden"
          >
            <!-- Subtle gradient overlay -->
            <div class="absolute inset-0 bg-gradient-to-br from-slate-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

            <!-- Header -->
            <div class="flex items-start justify-between mb-4 relative z-10">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center group-hover:bg-slate-200 transition-colors duration-200">
                  <FileText class="w-5 h-5 text-slate-600" />
                </div>
                <h4 class="text-lg font-medium text-slate-800 group-hover:text-slate-900 transition-colors duration-200 line-clamp-1">
                  {{ importItem.paper.title }}
                </h4>
              </div>
            </div>

            <!-- Authors -->
            <div class="mb-3 relative z-10">
              <p class="text-slate-600 text-sm line-clamp-2">
                {{ importItem.paper.authors.map(a => a.name).join(', ') }}
              </p>
            </div>

            <!-- Meta Info -->
            <div class="flex items-center gap-4 mb-4 relative z-10">
              <div class="flex items-center gap-1.5 text-slate-500 text-sm">
                <Clock class="w-4 h-4" />
                <span>{{ formatRelativeTime(importItem.importedAt) }}</span>
              </div>
              <div class="flex items-center gap-1.5 text-slate-500 text-sm">
                <Tag class="w-4 h-4" />
                <span>{{ importItem.paper.primaryCategory }}</span>
              </div>
            </div>

            <!-- Action -->
            <div class="border-t border-slate-100 pt-4 relative z-10">
              <router-link
                :to="`/workspace/${importItem.workspaceId}`"
                class="inline-flex items-center gap-2 text-slate-600 hover:text-slate-800 transition-colors duration-200 text-sm font-medium"
              >
                <ArrowRight class="w-4 h-4" />
                View in Workspace
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { PapersSearch } from '../index'
import type { ArxivPaper } from '../types'
import { FileText, Clock, Tag, ArrowRight } from 'lucide-vue-next'

interface Props {
  workspaceId?: string
}

defineProps<Props>()

interface ImportItem {
  paper: ArxivPaper
  workspaceId: string
  importedAt: Date
}

const recentImports = ref<ImportItem[]>([])

const handlePaperImported = (paper: ArxivPaper, workspaceId: string) => {
  // Add to recent imports
  recentImports.value.unshift({
    paper,
    workspaceId,
    importedAt: new Date()
  })
  
  // Keep only last 10 imports
  if (recentImports.value.length > 10) {
    recentImports.value = recentImports.value.slice(0, 10)
  }
  
  // Save to localStorage for persistence
  localStorage.setItem('arxiv-recent-imports', JSON.stringify(recentImports.value))
}

const formatRelativeTime = (date: Date) => {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins} minutes ago`
  if (diffHours < 24) return `${diffHours} hours ago`
  return `${diffDays} days ago`
}

onMounted(() => {
  // Load recent imports from localStorage
  const saved = localStorage.getItem('arxiv-recent-imports')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      recentImports.value = parsed.map((item: any) => ({
        ...item,
        importedAt: new Date(item.importedAt)
      }))
    } catch (error) {
      console.error('Error loading recent imports:', error)
    }
  }
})
</script>

<style scoped>
/* Line clamp utility for text truncation */
.line-clamp-1 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.line-clamp-2 {
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

/* Smooth focus transitions for accessibility */
button:focus,
input:focus {
  outline: 2px solid #1d4ed8;
  outline-offset: 2px;
}
</style>