<template>
  <div class="citations-list">
    <div class="citations-header" @click="toggleExpanded">
      <div class="citations-info">
        <Link class="citations-icon" />
        <span class="citations-count">{{ citations.length }} sources <span style="font-size: 0.8rem; color: var(--color-text-muted);"> [Internet]</span></span>
        <span class="citations-cost" v-if="totalCost">• ${{ totalCost }}</span>
      </div>
      <button class="citations-toggle">
        <ChevronDown v-if="isExpanded" class="toggle-icon" />
        <ChevronRight v-else class="toggle-icon" />
      </button>
    </div>

    <div v-if="isExpanded" class="citations-content">
      <div class="citations-grid">
        <div
          v-for="citation in citations"
          :key="citation.index"
          class="citation-item"
          :data-citation-index="citation.index"
        >
          <div class="citation-header">
            <h4 class="citation-title"><span class="citation-number" @click="handleCitationClick(citation)">[{{ citation.index }}]</span> {{ citation.title }}</h4>
            <a
              :href="citation.url"
              target="_blank"
              rel="noopener noreferrer"
              class="citation-link"
              @click.stop
            >
              <ExternalLink class="link-icon" />
            </a>
          </div>

          <div class="citation-content">
            <p class="citation-snippet" v-if="citation.snippet">
              {{ citation.snippet }}
            </p>
            <div class="citation-meta" v-if="citation.date || citation.last_updated">
              <span v-if="citation.date" class="citation-date">
                Published: {{ formatDate(citation.date) }}
              </span>
              <span v-if="citation.last_updated" class="citation-updated">
                Updated: {{ formatDate(citation.last_updated) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Link, ChevronDown, ChevronRight, ExternalLink } from 'lucide-vue-next'

interface Citation {
  index: number
  title: string
  url: string
  date: string
  snippet: string
  last_updated: string
}

interface Props {
  citations: Citation[]
  totalCost?: string
  onOpenPdf?: (citation: Citation) => void
}

const props = defineProps<Props>()

// Reactive state
const isExpanded = ref(false)

// Methods
const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}

const citations = props.citations // Use props to satisfy linter

const formatDate = (dateString: string) => {
  if (!dateString) return ''

  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return dateString
  }
}

const handleCitationClick = (citation: Citation) => {
  if (props.onOpenPdf) {
    // Call the PDF opening callback
    props.onOpenPdf(citation)
  } else {
    // Fallback to scrolling behavior
    scrollToCitation(citation.index)
  }
}

const scrollToCitation = (citationIndex: number) => {
  // Find the citation element and scroll to it
  const citationElement = document.querySelector(`[data-citation-index="${citationIndex}"]`)
  if (citationElement) {
    citationElement.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    })
    // Briefly highlight the citation
    citationElement.classList.add('citation-highlight')
    setTimeout(() => {
      citationElement.classList.remove('citation-highlight')
    }, 2000)
  }
}
</script>

<style scoped>
.citations-list {
  margin-top: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: var(--color-background-secondary);
}

.citations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  background-color: var(--color-background);
  border-bottom: 1px solid var(--color-border);
  transition: background-color 0.2s;
}

.citations-header:hover {
  background-color: var(--color-background-secondary);
}

.citations-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.citations-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-primary);
  flex-shrink: 0;
}

.citations-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-primary);
}

.citations-cost {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.citations-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  color: var(--color-text-muted);
  transition: all 0.2s;
}

.citations-toggle:hover {
  background-color: var(--color-background-tertiary);
  color: var(--color-text-primary);
}

.toggle-icon {
  width: 1rem;
  height: 1rem;
}

.citations-content {
  padding: 1rem;
}

.citations-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.citation-item {
  padding: 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.citation-item:hover {
  border-color: var(--color-border-focus);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.citation-item.citation-highlight {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2);
  animation: citation-pulse 2s ease-in-out;
}

@keyframes citation-pulse {
  0% { box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2); }
  50% { box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.4); }
  100% { box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.2); }
}

.citation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
}

.citation-number {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
  background-color: var(--color-primary-light);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
}

.citation-number:hover {
  background-color: var(--color-primary);
  color: white;
  transform: scale(1.05);
}

.citation-link {
  color: var(--color-text-muted);
  text-decoration: none;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.citation-link:hover {
  color: var(--color-primary);
  background-color: var(--color-primary-light);
}

.link-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.citation-content {
  flex: 1;
}

.citation-title {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.citation-title h4 {
  margin: 0;
}

.citation-snippet {
  margin: 0 0 0.75rem;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.citation-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.citation-date,
.citation-updated {
  font-weight: 500;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .citations-grid {
    gap: 0.75rem;
  }

  .citation-item {
    padding: 0.75rem;
  }

  .citation-meta {
    flex-direction: column;
    gap: 0.25rem;
  }
}
</style>
