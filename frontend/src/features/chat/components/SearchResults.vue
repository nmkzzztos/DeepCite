<template>
  <div v-if="searchResults && searchResults.length > 0" class="search-results">
    <div class="search-results__header" @click="expanded = !expanded">
      <div class="search-info">
        <FileText class="search-icon" />
        <span class="search-count">{{ groupedResults.length }} documents <span style="font-size: 0.8rem; color: var(--color-text-muted);"> [Workspaces]</span></span>
        <span class="search-cost" v-if="totalCost">• ${{ totalCost }}</span>
      </div>
      <button class="search-toggle">
        <ChevronDown v-if="expanded" class="toggle-icon" />
        <ChevronRight v-else class="toggle-icon" />
      </button>
    </div>
    
    <div v-if="expanded" class="search-results__content">
      <div
        v-for="docGroup in groupedResults"
        :key="docGroup.document.id"
        class="document-group"
      >
        <div class="document-header">
          <div class="document-source">
            <span class="source-number" @click="handleSourceClick(docGroup)">[{{
              docGroup.docIndex +
              (docGroup.pages.length > 0 ? ', P. ' + docGroup.pages.join(',') : '')
            }}]</span>
            <span class="document-title">{{ docGroup.document.title }}</span>
          </div>
        </div>

        <div class="document-results">
          <div
            v-for="(result, resultIndex) in docGroup.results"
            :key="result.paragraph_id"
            class="search-result"
            :data-result-index="getGlobalIndex(docGroup.docIndex, resultIndex)"
          >
            <div class="result-header" @click="handleResultClick(result, getGlobalIndex(docGroup.docIndex, resultIndex))">
              <div class="result-meta">
                <span v-if="result.page" class="page-info">Page {{ result.page }}</span>
                <span class="score">{{ Math.round(result.score * 100) }}% match</span>
              </div>
            </div>

            <div class="result-content">
              <div class="result-text">
                <div class="text-content">
                  {{ getTruncatedText(result) }}
                  <span v-if="shouldShowToggle(result) && !isTextExpanded(result.paragraph_id)" class="text-fade">...</span>
                </div>
                <button
                  v-if="shouldShowToggle(result)"
                  @click="toggleText(result.paragraph_id)"
                  class="text-toggle"
                >
                  {{ isTextExpanded(result.paragraph_id) ? 'Show less' : 'Show more' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { FileText, ChevronDown, ChevronRight } from 'lucide-vue-next'

const TEXT_TRUNCATE_LENGTH = 100

interface SearchResult {
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
}

interface Props {
  searchResults?: SearchResult[]
  totalCost?: string
  onOpenPdf?: (result: SearchResult, index: number) => void
}

const props = defineProps<Props>()

const expanded = ref(false)
const expandedTexts = ref(new Set<string>())

// Group search results by document
const groupedResults = computed(() => {
  if (!props.searchResults) return []

  const groups: Array<{
    document: SearchResult['document']
    results: SearchResult[]
    pages: number[]
    docIndex: number
  }> = []

  const documentMap = new Map<string, SearchResult[]>()

  // Group by document ID
  props.searchResults.forEach(result => {
    if (!documentMap.has(result.document.id)) {
      documentMap.set(result.document.id, [])
    }
    documentMap.get(result.document.id)!.push(result)
  })

  // Convert to array with document index
  let docIndex = 1
  documentMap.forEach((results) => {
    const pages = [...new Set(results.map(r => r.page).filter(p => p !== undefined))].sort((a, b) => a! - b!)
    groups.push({
      document: results[0].document,
      results,
      pages,
      docIndex: docIndex++
    })
  })

  return groups
})

const handleSourceClick = (docGroup: any) => {
  // For document-level clicks, open the first result of the document
  if (docGroup.results && docGroup.results.length > 0) {
    const firstResult = docGroup.results[0]
    if (props.onOpenPdf) {
      props.onOpenPdf(firstResult, docGroup.docIndex)
    }
  }
}

const handleResultClick = (result: SearchResult, globalIndex: number) => {
  if (props.onOpenPdf) {
    // Call the PDF opening callback with the global index
    props.onOpenPdf(result, globalIndex)
  } else {
    // Fallback to scrolling behavior
    scrollToResult(globalIndex)
  }
}

const getGlobalIndex = (docIndex: number, resultIndex: number): number => {
  // Calculate the global index based on document position
  // This is needed for backwards compatibility with existing click handlers
  let globalIndex = 0
  for (let i = 1; i < docIndex; i++) {
    const group = groupedResults.value.find(g => g.docIndex === i)
    if (group) {
      globalIndex += group.results.length
    }
  }
  return globalIndex + resultIndex + 1
}

const scrollToResult = (index: number) => {
  const resultElement = document.querySelector(`[data-result-index="${index}"]`)
  if (resultElement) {
    resultElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
    // Briefly highlight the result
    resultElement.classList.add('result-highlight')
    setTimeout(() => {
      resultElement.classList.remove('result-highlight')
    }, 2000)
  }
}

const isTextExpanded = (paragraphId: string): boolean => {
  return expandedTexts.value.has(paragraphId)
}

const toggleText = (paragraphId: string) => {
  if (expandedTexts.value.has(paragraphId)) {
    expandedTexts.value.delete(paragraphId)
  } else {
    expandedTexts.value.add(paragraphId)
  }
}

const getTruncatedText = (result: SearchResult): string => {
  if (isTextExpanded(result.paragraph_id)) {
    return result.text
  }
  return result.text.length > TEXT_TRUNCATE_LENGTH
    ? result.text.substring(0, TEXT_TRUNCATE_LENGTH)
    : result.text
}

const shouldShowToggle = (result: SearchResult): boolean => {
  return result.text.length > TEXT_TRUNCATE_LENGTH
}
</script>

<style scoped>
.search-results {
  margin-top: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: var(--color-background-secondary);
}

.search-results__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  background-color: var(--color-background);
  border-bottom: 1px solid var(--color-border);
  transition: background-color 0.2s;
}

.search-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-results__header:hover {
  background-color: var(--color-background-secondary);
}

.search-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.search-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.search-cost {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.search-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  color: var(--color-text-muted);
  transition: all 0.2s;
}

.search-toggle:hover {
  background-color: var(--color-background-tertiary);
  color: var(--color-text-primary);
}

.toggle-icon {
  width: 1rem;
  height: 1rem;
  transition: transform 0.2s;
}

.toggle-icon.expanded {
  transform: rotate(180deg);
}

.search-results__content {
  padding: 1rem;
}

.document-group {
  margin-bottom: 2rem;
}

.document-group:last-child {
  margin-bottom: 0;
}

.document-header {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.document-source {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.document-results {
  margin-left: 1rem;
}

.search-result {
  padding: 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  margin-bottom: 0.75rem;
  transition: all 0.2s;
  cursor: pointer;
}

.search-result:hover {
  border-color: var(--color-border-focus);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.search-result.result-highlight {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2);
  animation: result-pulse 2s ease-in-out;
}

@keyframes result-pulse {
  0% { box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2); }
  50% { box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.4); }
  100% { box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2); }
}

.search-result:last-child {
  margin-bottom: 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  gap: 1rem;
}

.result-source {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.source-number {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
  background-color: var(--color-primary-light);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.2s;
}

.source-number:hover {
  background-color: var(--color-primary);
  color: white;
  transform: scale(1.05);
}

.document-title {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  width: 100%;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.authors {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.year {
  white-space: nowrap;
}

.score {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-weight: 500;
  white-space: nowrap;
}

.result-content {
  font-size: 0.875rem;
}

.section-path,
.page-info {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

.result-text {
  color: var(--color-text-primary);
  line-height: 1.5;
  padding: 0.5rem;
  background-color: var(--color-background-secondary);
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.text-content {
  display: inline;
}

.text-fade {
  color: var(--color-text-muted);
  font-weight: 500;
}

.text-toggle {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.125rem 0.25rem;
  margin-left: 0.5rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
  text-decoration: underline;
}

.text-toggle:hover {
  background-color: var(--color-primary-light);
  color: var(--color-primary);
  text-decoration: none;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .search-results__content {
    padding: 0.75rem;
  }

  .document-group {
    margin-bottom: 1.5rem;
  }

  .document-source {
    gap: 0.5rem;
  }

  .document-results {
    margin-left: 0.5rem;
  }

  .search-result {
    padding: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .result-header {
    gap: 0.75rem;
  }

  .result-meta {
    flex-direction: column;
    gap: 0.25rem;
    align-items: flex-start;
  }
}
</style>