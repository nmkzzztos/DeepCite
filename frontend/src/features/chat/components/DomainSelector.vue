<template>
    <div v-if="isOpen" class="modal-overlay" @click="handleOverlayClick">
        <div class="modal-content" @click.stop>
            <div class="modal-header">
                <h3>Select Search Domains</h3>
                <button @click="close" class="close-button">
                    <X class="close-icon" />
                </button>
            </div>

            <div class="modal-body">
                <!-- Add custom domain -->
                <div class="add-domain-section">
                    <div class="input-group">
                        <input v-model="newDomain" @keydown.enter="addCustomDomain"
                            placeholder="Enter domain (e.g., github.com)" class="domain-input" ref="domainInput" />
                        <button @click="addCustomDomain" :disabled="!newDomain.trim()" class="add-button">
                            <Plus class="add-icon" />
                            Add
                        </button>
                    </div>
                </div>

                <!-- Domain Groups -->
                <div class="domain-groups-section">
                    <div v-for="(group, groupKey) in domainGroups" :key="groupKey" class="domain-group">
                        <div class="group-header" @click="toggleGroupExpansion(groupKey)">
                            <div class="group-title-row">
                                <div class="group-info">
                                    <div :class="['expand-icon', { 'expanded': isGroupExpanded(groupKey) }]">
                                        <ChevronRight class="chevron-icon" />
                                    </div>
                                    <h4>{{ group.name }}</h4>
                                </div>
                                <div class="group-controls">
                                    <span class="group-count">{{ getSelectedCountInGroup(groupKey) }}/{{ group.domains.length }}</span>
                                    <button @click.stop="toggleGroup(groupKey)" class="group-select-btn">
                                        <div :class="['group-checkbox', { 'selected': isGroupFullySelected(groupKey) }]">
                                            <Check v-if="isGroupFullySelected(groupKey)" class="check-icon" />
                                        </div>
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div v-if="isGroupExpanded(groupKey)" class="domain-tags">
                            <button v-for="domain in group.domains" :key="domain" @click="toggleDomain(domain)"
                                :class="['domain-tag', { 'selected': selectedDomains.has(domain) }]">
                                {{ domain }}
                                <X v-if="selectedDomains.has(domain)" class="remove-icon" />
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Selected domains -->
                <div v-if="selectedDomains.size > 0" class="selected-domains-section">
                    <h4>Selected Domains ({{ selectedDomains.size }})</h4>
                    <div class="domain-tags">
                        <button v-for="domain in Array.from(selectedDomains)" :key="domain"
                            @click="toggleDomain(domain)" class="domain-tag selected">
                            {{ domain }}
                            <X class="remove-icon" />
                        </button>
                    </div>
                </div>

                <!-- No domains selected -->
                <div v-else class="no-selection">
                    <Globe class="no-selection-icon" />
                    <p>No domains selected. Search will use all available sources.</p>
                </div>
            </div>

            <div class="modal-footer">
                <div class="selection-summary">
                    <span>{{ selectedDomains.size }} domains selected</span>
                </div>

                <div class="modal-actions">
                    <button @click="clearSelection" class="clear-button">Clear All</button>
                    <button @click="close" class="cancel-button">Cancel</button>
                    <button @click="applySelection" class="apply-button">Apply Selection</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { X, Plus, Globe, Check, ChevronRight } from 'lucide-vue-next'

interface Props {
    isOpen: boolean
    initialSelection?: string[]
}

interface Emits {
    (e: 'close'): void
    (e: 'apply', domains: string[]): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// State
const newDomain = ref('')
const selectedDomains = ref<Set<string>>(new Set())
const domainInput = ref<HTMLInputElement>()
const expandedGroups = ref<Set<string>>(new Set())

// Organized domain groups for quick selection
const domainGroups = {
    core_academic: {
        name: 'Core Academic',
        domains: [
            'arxiv.org',
            'semanticscholar.org',
            'crossref.org',
            'doaj.org',
            'core.ac.uk',
            'base-search.net',
            'zenodo.org',
            'openaire.eu',
            'europepmc.org'
        ]
    },
    preprints: {
        name: 'Preprints',
        domains: [
            'arxiv.org',
            'biorxiv.org',
            'medrxiv.org',
            'osf.io',
            'researchsquare.com',
            'preprints.org',
            'ssrn.com',
            'hal.science'
        ]
    },
    publishers: {
        name: 'Major Publishers',
        domains: [
            'nature.com',
            'science.org',
            'pnas.org',
            'cell.com',
            'springer.com',
            'wiley.com',
            'sciencedirect.com',
            'tandfonline.com',
            'plos.org',
            'biomedcentral.com'
        ]
    },
    medicine: {
        name: 'Medicine & Health',
        domains: [
            'pubmed.ncbi.nlm.nih.gov',
            'ncbi.nlm.nih.gov/pmc',
            'clinicaltrials.gov',
            'who.int',
            'nejm.org',
            'thelancet.com',
            'bmj.com',
            'jamanetwork.com',
            'cochranelibrary.com'
        ]
    },
    ai_cs: {
        name: 'AI & Computer Science',
        domains: [
            'arxiv.org',
            'openreview.net',
            'nips.cc',
            'icml.cc',
            'iclr.cc',
            'aaai.org',
            'aclanthology.org',
            'dl.acm.org',
            'ieeexplore.ieee.org'
        ]
    },
    physics_math: {
        name: 'Physics & Mathematics',
        domains: [
            'arxiv.org',
            'journals.aps.org',
            'aip.scitation.org',
            'iopscience.iop.org',
            'siam.org',
            'projecteuclid.org',
            'nature.com',
            'springer.com'
        ]
    },
    chemistry: {
        name: 'Chemistry & Materials',
        domains: [
            'pubs.acs.org',
            'pubs.rsc.org',
            'nature.com',
            'sciencedirect.com',
            'wiley.com',
            'springer.com',
            'rsc.org',
            'chemrxiv.org'
        ]
    },
    earth_science: {
        name: 'Earth & Climate Science',
        domains: [
            'agu.org',
            'agupubs.onlinelibrary.wiley.com',
            'copernicus.org',
            'gmd.copernicus.org',
            'nasa.gov',
            'noaa.gov',
            'nature.com',
            'sciencedirect.com'
        ]
    },
    economics: {
        name: 'Economics & Social Sciences',
        domains: [
            'nber.org',
            'ideas.repec.org',
            'ssrn.com',
            'jstor.org',
            'oecd-ilibrary.org',
            'imf.org',
            'worldbank.org',
            'apsanet.org',
            'sagepub.com',
            'tandfonline.com'
        ]
    },
    psychology: {
        name: 'Psychology & Neuroscience',
        domains: [
            'psycnet.apa.org',
            'nature.com',
            'cell.com/neuron',
            'biorxiv.org',
            'medrxiv.org',
            'elifesciences.org',
            'frontiersin.org',
            'sciencedirect.com'
        ]
    },
    engineering: {
        name: 'Engineering & Technology',
        domains: [
            'ieeexplore.ieee.org',
            'dl.acm.org',
            'asmedigitalcollection.asme.org',
            'saemobilus.sae.org',
            'springer.com',
            'wiley.com',
            'sciencedirect.com',
            'usenix.org'
        ]
    },
    government: {
        name: 'Government & Agencies',
        domains: [
            'nih.gov',
            'ncbi.nlm.nih.gov',
            'who.int',
            'ema.europa.eu',
            'fda.gov',
            'cdc.gov',
            'nice.org.uk'
        ]
    }
}

// Methods
const addCustomDomain = () => {
    const domain = newDomain.value.trim().toLowerCase()

    if (!domain) return

    // Basic domain validation
    if (!isValidDomain(domain)) {
        alert('Please enter a valid domain (e.g., example.com)')
        return
    }

    selectedDomains.value.add(domain)
    newDomain.value = ''

    // Focus back to input
    nextTick(() => {
        domainInput.value?.focus()
    })
}

const isValidDomain = (domain: string): boolean => {
    // Simple domain validation regex
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*(\.[a-zA-Z]{2,})+$/
    return domainRegex.test(domain)
}

const toggleDomain = (domain: string) => {
    if (selectedDomains.value.has(domain)) {
        selectedDomains.value.delete(domain)
    } else {
        selectedDomains.value.add(domain)
    }
}

type DomainGroupKey = keyof typeof domainGroups

const toggleGroup = (groupKey: DomainGroupKey) => {
    const group = domainGroups[groupKey]
    if (!group) return

    const groupDomains = new Set(group.domains)
    const selectedInGroup = Array.from(selectedDomains.value).filter(domain => groupDomains.has(domain))

    if (selectedInGroup.length === group.domains.length) {
        // All domains in group are selected, remove them all
        group.domains.forEach(domain => selectedDomains.value.delete(domain))
    } else {
        // Add all domains from group
        group.domains.forEach(domain => selectedDomains.value.add(domain))
    }
}

const isGroupFullySelected = (groupKey: DomainGroupKey): boolean => {
    const group = domainGroups[groupKey]
    if (!group) return false

    return group.domains.every(domain => selectedDomains.value.has(domain))
}

const getSelectedCountInGroup = (groupKey: DomainGroupKey): number => {
    const group = domainGroups[groupKey]
    if (!group) return 0

    return group.domains.filter(domain => selectedDomains.value.has(domain)).length
}

const clearSelection = () => {
    selectedDomains.value.clear()
}

const applySelection = () => {
    const domains = Array.from(selectedDomains.value)
    emit('apply', domains)
    close()
}

const close = () => {
    emit('close')
}

const handleOverlayClick = (event: MouseEvent) => {
    if (event.target === event.currentTarget) {
        close()
    }
}

const toggleGroupExpansion = (groupKey: DomainGroupKey) => {
    if (expandedGroups.value.has(groupKey)) {
        expandedGroups.value.delete(groupKey)
    } else {
        expandedGroups.value.add(groupKey)
    }
}

const isGroupExpanded = (groupKey: DomainGroupKey): boolean => {
    return expandedGroups.value.has(groupKey)
}

// Initialize selection from props
const initializeSelection = () => {
    if (props.initialSelection) {
        selectedDomains.value = new Set(props.initialSelection)
    }
}

// Watchers
const initializeWhenOpened = () => {
    if (props.isOpen) {
        initializeSelection()
        nextTick(() => {
            domainInput.value?.focus()
        })
    }
}

// Initialize when component mounts or opens
onMounted(() => {
  initializeWhenOpened()
})

// Watch for isOpen changes
watch(() => props.isOpen, (isOpen: boolean) => {
  if (isOpen) {
    initializeWhenOpened()
  }
})
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
}

.modal-content {
    background-color: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 0.75rem;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    max-width: 600px;
    max-height: 80vh;
    width: 90vw;
    display: flex;
    flex-direction: column;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem;
    border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-text-primary);
}

.close-button {
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.5rem;
    color: var(--color-text-muted);
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.close-button:hover {
    background-color: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
    color: #dc2626;
    transform: scale(1.05);
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.close-button:active {
    transform: scale(0.95);
}

.close-icon {
    width: 1.125rem;
    height: 1.125rem;
}

.modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    max-height: calc(80vh - 140px);
}

/* Custom scrollbar styles */
.modal-body::-webkit-scrollbar {
    width: 6px;
}

.modal-body::-webkit-scrollbar-track {
    background: var(--color-background-secondary);
    border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 3px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
    background: var(--color-border-focus);
}

.add-domain-section {
    margin-bottom: 1.5rem;
}

.input-group {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.domain-input {
    flex: 1;
    padding: 0.625rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background-color: var(--color-background);
    color: var(--color-text-primary);
    font-size: 0.85rem;
    transition: border-color 0.2s;
}

.domain-input:focus {
    outline: none;
    border-color: var(--color-border-focus);
    box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.15);
}

.add-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
    color: white;
    border: 1px solid var(--color-primary);
    border-radius: 0.5rem;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
    position: relative;
    overflow: hidden;
}

.add-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.add-button:hover:not(:disabled) {
    background: linear-gradient(135deg, var(--color-primary-hover) 0%, #1d4ed8 100%);
    border-color: var(--color-primary-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}

.add-button:hover:not(:disabled)::before {
    left: 100%;
}

.add-button:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}

.add-button:disabled {
    background: linear-gradient(135deg, var(--color-text-muted) 0%, #64748b 100%);
    border-color: var(--color-text-muted);
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
}

.add-button:disabled::before {
    display: none;
}

.add-icon {
    width: 0.875rem;
    height: 0.875rem;
}

.domain-groups-section,
.selected-domains-section {
    margin-bottom: 1.5rem;
}

.domain-groups-section h4,
.selected-domains-section h4 {
    margin: 0 0 0.75rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--color-text-primary);
}

.domain-group {
    margin-bottom: 0.75rem;
}

.domain-group:last-child {
    margin-bottom: 0;
}

.domain-groups-section h4 {
    padding-bottom: 0.25rem;
    margin-bottom: 0;
}

.group-header {
    cursor: pointer;
    padding: 0.5rem 0.75rem;
    border: 1px solid transparent;
    border-radius: 0.5rem;
    transition: all 0.2s;
    margin-bottom: 0.5rem;
}

.group-header:hover {
    border-color: var(--color-border-focus);
    background-color: rgba(29, 78, 216, 0.02);
}

.group-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.group-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.group-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.expand-icon {
    width: 1rem;
    height: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s ease;
    color: var(--color-text-muted);
}

.expand-icon.expanded {
    transform: rotate(90deg);
}

.chevron-icon {
    width: 1rem;
    height: 1rem;
}

.group-select-btn {
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.group-select-btn:hover {
    background-color: rgba(29, 78, 216, 0.1);
    border-color: var(--color-primary);
    transform: scale(1.05);
}

.group-select-btn:active {
    transform: scale(0.95);
}

.group-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.group-count {
    font-size: 0.875rem;
    color: var(--color-text-muted);
    font-weight: 500;
}

.group-checkbox {
    width: 1.125rem;
    height: 1.125rem;
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--color-background);
    transition: all 0.2s;
}

.group-checkbox.selected {
    background-color: var(--color-primary);
    border-color: var(--color-primary);
}

.check-icon {
    width: 0.75rem;
    height: 0.75rem;
    color: white;
}

.domain-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    padding-left: 1.5rem;
    margin-top: 0.5rem;
}

.domain-tag {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.625rem;
    background-color: transparent;
    border: 1px solid var(--color-border);
    border-radius: 0.75rem;
    cursor: pointer;
    font-size: 0.8rem;
    color: var(--color-text-primary);
    transition: all 0.2s;
    line-height: 1.2;
}

.domain-tag:hover {
    border-color: var(--color-border-focus);
    background-color: rgba(29, 78, 216, 0.05);
}

.domain-tag.selected {
    border-color: var(--color-primary);
    background-color: rgba(29, 78, 216, 0.1);
    color: var(--color-primary);
    font-weight: 500;
}

.remove-icon {
    width: 0.75rem;
    height: 0.75rem;
    flex-shrink: 0;
}

.no-selection {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1.5rem;
    text-align: center;
    color: var(--color-text-muted);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    background-color: rgba(255, 255, 255, 0.02);
}

.no-selection-icon {
    width: 2.5rem;
    height: 2.5rem;
    margin-bottom: 0.75rem;
    opacity: 0.5;
}

.no-selection p {
    margin: 0;
    font-size: 0.85rem;
}

.modal-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--color-border);
    border-radius: 0 0 0.75rem 0.75rem;
}

.selection-summary {
    font-size: 0.85rem;
    color: var(--color-text-muted);
}

.modal-actions {
    display: flex;
    gap: 0.5rem;
}

.clear-button,
.cancel-button,
.apply-button {
    padding: 0.5rem 0.875rem;
    border: 1px solid transparent;
    border-radius: 0.5rem;
    cursor: pointer;
    font-weight: 500;
    font-size: 0.85rem;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.clear-button {
    background-color: transparent;
    color: var(--color-text-muted);
    border-color: var(--color-border);
}

.clear-button:hover {
    border-color: #f59e0b;
    background-color: rgba(245, 158, 11, 0.1);
    color: #d97706;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

.clear-button:active {
    transform: translateY(0);
}

.cancel-button {
    background-color: transparent;
    color: var(--color-text-primary);
    border-color: var(--color-border);
}

.cancel-button:hover {
    border-color: var(--color-border-focus);
    background-color: rgba(29, 78, 216, 0.08);
    color: var(--color-primary);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
}

.cancel-button:active {
    transform: translateY(0);
}

.apply-button {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
    color: white;
    border-color: var(--color-primary);
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}

.apply-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.apply-button:hover {
    background: linear-gradient(135deg, var(--color-primary-hover) 0%, #1d4ed8 100%);
    border-color: var(--color-primary-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}

.apply-button:hover::before {
    left: 100%;
}

.apply-button:active {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}
</style>
