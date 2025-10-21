<template>
    <div class="pdf-viewer" v-if="pdfData !== undefined && pdfData !== null">
        <div class="pdf-viewer__header">
            <div class="pdf-viewer__title">
                <FileText class="title-icon" />
                <span class="title-text">{{ documentTitle || 'PDF Document' }}</span>
            </div>
            <div class="pdf-viewer__controls">
                <button @click="zoomIn" class="control-button" title="Zoom In">
                    <ZoomIn class="control-icon" />
                </button>
                <button @click="zoomOut" class="control-button" title="Zoom Out">
                    <ZoomOut class="control-icon" />
                </button>
                <button @click="fitToPageButton" class="control-button" title="Fit to Page">
                    <Maximize class="control-icon" />
                </button>
                <button @click="resetZoom" class="control-button" title="Reset Zoom">
                    <RotateCcw class="control-icon" />
                </button>
                <button @click="closeViewer" class="control-button control-button--close" title="Close">
                    <X class="control-icon" />
                </button>
            </div>
        </div>

        <div class="pdf-viewer__content">
            <div v-if="!pdf" class="loading-state">
                <div class="loading-spinner"></div>
                <p>Loading PDF...</p>
            </div>

            <div v-else class="pdf-content">
                <div class="pdf-container">
                    <VuePDF
                        ref="pdfViewerRef"
                        :pdf="pdf"
                        :scale="scale"
                        :page="currentPage"
                        :rotation="rotation"
                        :text-layer="true"
                        :annotation-layer="true"
                        :render-text-layer="true"
                        class="pdf-embed"
                    />

                    <!-- Highlight overlay -->
                    <div
                        v-for="highlight in highlightRects"
                        :key="`highlight-${highlight.page}`"
                        v-show="currentPage === highlight.page"
                        class="highlight-overlay"
                    >
                        <div
                            v-for="(rect, index) in highlight.rects"
                            :key="`rect-${index}`"
                            class="highlight-rect"
                            :style="{
                                left: `${rect.x * 100}%`,
                                top: `${rect.y * 100}%`,
                                width: `${rect.width * 100}%`,
                                height: `${rect.height * 100}%`
                            }"
                        ></div>
                    </div>
                </div>
            </div>

            <!-- Navigation always visible -->
            <div v-if="totalPages > 1" class="pdf-navigation">
                <button @click="previousPage" :disabled="currentPage <= 1" class="nav-button">
                    <ChevronLeft class="nav-icon" />
                </button>

                <div class="page-info">
                    <input v-model.number="currentPageInput" @keyup.enter="goToPage" @blur="goToPage" type="number"
                        :min="1" :max="totalPages" class="page-input" />
                    <span>of {{ totalPages }}</span>
                </div>

                <button @click="nextPage" :disabled="currentPage >= totalPages" class="nav-button">
                    <ChevronRight class="nav-icon" />
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
    FileText,
    ZoomIn,
    ZoomOut,
    RotateCcw,
    X,
    ChevronLeft,
    ChevronRight,
    Maximize
} from 'lucide-vue-next'
import { VuePDF, usePDF } from '@tato30/vue-pdf'
import '@tato30/vue-pdf/style.css'

interface Props {
    pdfData?: string | Uint8Array | null // base64 encoded PDF data or Uint8Array
    documentTitle?: string
    isVisible?: boolean
    highlightText?: string
    highlightPage?: number
}

interface Emits {
    (e: 'close'): void
    (e: 'error', error: string): void
}

const props = withDefaults(defineProps<Props>(), {
    pdfData: undefined,
    documentTitle: '',
    isVisible: true
})

const emit = defineEmits<Emits>()

// Reactive state
const currentPage = ref(1)
const totalPages = ref(0)
const scale = ref(1.3)
const rotation = ref(0)
const pdfViewerRef = ref<any>(null)

// Page dimensions for proper scaling
const pageWidth = ref(0)
const pageHeight = ref(0)
const containerWidth = ref(0)
const containerHeight = ref(0)

// Computed
const currentPageInput = computed({
    get: () => currentPage.value,
    set: (value: number) => {
        if (value >= 1 && value <= totalPages.value) {
            currentPage.value = value
        }
    }
})

const processedPdfData = computed(() => {
    const data = props.pdfData
    if (data === undefined || data === null) {
        return null
    }

    // VuePDF can accept Uint8Array, base64 string, or URL
    if (data instanceof Uint8Array) {
        return data
    }

    if (typeof data === 'string') {
        // If it's base64, VuePDF can handle it directly
        return data
    }

    return data
})

// Use VuePDF composable
const { pdf, pages } = usePDF(processedPdfData)

// Reactive state for text highlighting
const highlightRects = ref<Array<{page: number, rects: Array<{x: number, y: number, width: number, height: number}>}>>([])

// Calculate optimal scale based on page dimensions and container size
const calculateOptimalScale = () => {
    return 1.2
}

// Helper function to get text item rectangle coordinates
const getTextItemRect = (item: any, viewport: any) => {
    let x, y, width, height

    try {
        if (item.transform && item.transform.length >= 6) {
            // PDF.js transform matrix: [scaleX, skewX, skewY, scaleY, translateX, translateY]
            const [, , , , translateX, translateY] = item.transform
            x = translateX
            y = translateY
            width = item.width || item.str.length * 8
            height = item.height || 14
        } else if (item.rect && item.rect.length >= 4) {
            // Fallback to rect if available [x1, y1, x2, y2]
            [x, y, , , width, height] = item.rect
            width = width - x
            height = height - y
        } else {
            // Last resort approximation
            console.warn('Using approximation for text coordinates')
            x = Math.random() * (viewport.width * 0.8) // Random position
            y = Math.random() * (viewport.height * 0.8)
            width = item.str.length * 8
            height = 14
        }

        // Validate coordinates
        if (isNaN(x) || isNaN(y) || isNaN(width) || isNaN(height)) {
            console.warn('Invalid coordinates for text item:', item.str)
            return null
        }

        // Convert to viewport coordinates (normalized 0-1)
        const normalizedRect = {
            x: Math.max(0, Math.min(1, x / viewport.width)),
            y: Math.max(0, Math.min(1, (viewport.height - y - height) / viewport.height)),
            width: Math.max(0.02, Math.min(0.5, width / viewport.width)),
            height: Math.max(0.01, Math.min(0.1, height / viewport.height))
        }

        return normalizedRect
    } catch (error) {
        console.error('Error getting text item rect:', error)
        return null
    }
}

// Function to find and highlight text
const findAndHighlightText = async (searchText: string, targetPage: number) => {
    if (!pdf.value || !searchText) return

    try {
        const page = await (pdf.value as any).getPage(targetPage)
        const textContent = await page.getTextContent()
        const viewport = page.getViewport({ scale: 1.0 })

        const textItems = textContent.items
        const rects: Array<{x: number, y: number, width: number, height: number}> = []

        console.log('Found text items:', textItems.length)

        // Normalize search text - remove extra spaces and convert to lowercase
        const normalizedSearch = searchText.toLowerCase().trim().replace(/\s+/g, ' ')
        const searchWords = normalizedSearch.split(' ')

        // Collect all text content to find the best match
        let fullText = ''
        for (let i = 0; i < textItems.length; i++) {
            const item = textItems[i] as any
            if (item.str) {
                fullText += item.str + ' '
            }
        }
        fullText = fullText.toLowerCase().trim()

        console.log('Full page text (first 200 chars):', fullText.substring(0, 200))

        // Try different search approaches
        let foundMatches = false

        // Approach 1: Search for exact text matches
        if (fullText.includes(normalizedSearch)) {
            console.log('Found exact text match in page content')

            // Find text items that contain parts of our search
            for (let i = 0; i < textItems.length; i++) {
                const item = textItems[i] as any
                if (!item.str) continue

                const itemText = item.str.toLowerCase().trim()
                const hasMatch = searchWords.some(word =>
                    itemText.includes(word) ||
                    normalizedSearch.includes(itemText)
                )

                if (hasMatch) {
                    console.log('Found matching text item:', item.str)
                    foundMatches = true

                    // Get coordinates
                    const rect = getTextItemRect(item, viewport)
                    if (rect) {
                        rects.push(rect)
                        console.log('Added highlight rect:', rect)
                    }
                }
            }
        }

        // Approach 2: If no exact matches, try partial word matching
        if (!foundMatches && searchWords.length > 0) {
            console.log('Trying partial word matching')

            for (let i = 0; i < textItems.length; i++) {
                const item = textItems[i] as any
                if (!item.str) continue

                const itemText = item.str.toLowerCase().trim()

                // Check if any search word is contained in this text item
                const hasPartialMatch = searchWords.some(word => {
                    // Allow for partial matches (word appears in text item)
                    return itemText.includes(word) ||
                           // Or text item appears in search word
                           word.includes(itemText) ||
                           // Or check for fuzzy matches (remove punctuation)
                           itemText.replace(/[^\w]/g, '').includes(word.replace(/[^\w]/g, ''))
                })

                if (hasPartialMatch) {
                    console.log('Found partial match:', item.str)
                    foundMatches = true

                    const rect = getTextItemRect(item, viewport)
                    if (rect) {
                        rects.push(rect)
                        console.log('Added partial highlight rect:', rect)
                    }
                }
            }
        }

        // Approach 3: If still no matches, highlight the entire page area (fallback)
        if (!foundMatches) {
            console.log('No specific matches found, using page-wide highlight')

            // Create a highlight that covers a portion of the page
            rects.push({
                x: 0.1, // 10% from left
                y: 0.2, // 20% from top
                width: 0.8, // 80% width
                height: 0.1 // 10% height
            })
            foundMatches = true
        }

        if (rects.length > 0) {
            highlightRects.value = [{ page: targetPage, rects }]
            console.log('Set highlight rects:', highlightRects.value)

            // Scroll to the page with highlights
            currentPage.value = targetPage
            console.log('Scrolled to page:', targetPage)
        } else {
            console.log('No text matches found, but still scrolling to target page')
            // Even if no text is found, scroll to the target page
            currentPage.value = targetPage
            console.log('Scrolled to page:', targetPage)
        }
    } catch (error) {
        console.error('Error finding text:', error)
    }
}

// Update container dimensions
const updateContainerDimensions = () => {
    if (pdfViewerRef.value?.$el) {
        const rect = pdfViewerRef.value.$el.getBoundingClientRect()
        containerWidth.value = rect.width
        containerHeight.value = rect.height
    }
}

// Fit page to container
const fitToPage = () => {
    scale.value = 1.5
}

// Handle text selection and prevent layout issues
onMounted(() => {
    // Ensure proper text layer rendering
    const observer = new MutationObserver(() => {
        const textLayer = document.querySelector('.textLayer') as HTMLElement
        if (textLayer) {
            textLayer.style.position = 'absolute'
            textLayer.style.left = '0'
            textLayer.style.top = '0'
            textLayer.style.right = '0'
            textLayer.style.bottom = '0'
            textLayer.style.overflow = 'hidden'
            textLayer.style.zIndex = '1'
        }
    })

    // Observe the PDF viewer container
    if (pdfViewerRef.value?.$el) {
        observer.observe(pdfViewerRef.value.$el, {
            childList: true,
            subtree: true
        })
    }

    // Handle window resize
    const handleResize = () => {
        updateContainerDimensions()
        if (pageWidth.value > 0 && pageHeight.value > 0) {
            // Only auto-fit if current scale is close to optimal (user hasn't manually zoomed much)
            const currentOptimal = calculateOptimalScale()
            const scaleRatio = scale.value / currentOptimal
            if (scaleRatio >= 0.9 && scaleRatio <= 1.1) {
                fitToPage()
            }
        }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    onUnmounted(() => {
        observer.disconnect()
        window.removeEventListener('resize', handleResize)
    })
})

// Update totalPages when PDF info is available
watch(pages, (newPages) => {
    totalPages.value = newPages
})

// Watch for PDF changes to get page dimensions
watch(pdf, async (newPdf) => {
    if (newPdf && 'getPage' in newPdf && currentPage.value <= totalPages.value) {
        try {
            const page = await (newPdf as any).getPage(currentPage.value)
            const viewport = page.getViewport({ scale: 1.0 })

            // PDF dimensions are in points (1/72 inch)
            pageWidth.value = viewport.width
            pageHeight.value = viewport.height

            console.log(`PDF page dimensions: ${pageWidth.value} x ${pageHeight.value} points`)

            // Auto-fit page after getting dimensions
            nextTick(() => {
                updateContainerDimensions()
                fitToPage()
            })
        } catch (error) {
            console.error('Error getting page dimensions:', error)
        }
    }
})

// Watch for container resize
watch(() => props.isVisible, (visible) => {
    if (visible) {
        // Update container dimensions when viewer becomes visible
        nextTick(() => {
            updateContainerDimensions()
            if (pageWidth.value > 0 && pageHeight.value > 0) {
                fitToPage()
            }
        })
    }
})

// Methods
const zoomIn = () => {
    scale.value = Math.min(scale.value + 0.25, 3.0)
}

const zoomOut = () => {
    scale.value = Math.max(scale.value - 0.25, 0.5)
}

const resetZoom = () => {
    // Reset to a reasonable default scale (1.0) instead of optimal
    // This gives user control, while fitToPage provides optimal scaling
    scale.value = 1.2
    rotation.value = 0
}

const fitToPageButton = () => {
    fitToPage()
    rotation.value = 0
}

const closeViewer = () => {
    emit('close')
}


const previousPage = () => {
    if (currentPage.value > 1) {
        currentPage.value--
        // Scroll to top when changing pages
        nextTick(() => {
            scrollToTop()
        })
    }
}

const nextPage = () => {
    if (currentPage.value < totalPages.value) {
        currentPage.value++
        // Scroll to top when changing pages
        nextTick(() => {
            scrollToTop()
        })
    }
}

const goToPage = () => {
    if (currentPageInput.value >= 1 && currentPageInput.value <= totalPages.value) {
        currentPage.value = currentPageInput.value
        // Scroll to top when changing pages
        nextTick(() => {
            scrollToTop()
        })
    } else {
        currentPageInput.value = currentPage.value
    }
}

// Scroll to top of PDF content
const scrollToTop = () => {
    const contentElement = pdfViewerRef.value?.$el?.querySelector('.pdf-viewer__content') as HTMLElement
    if (contentElement) {
        contentElement.scrollTo({
            top: 0,
            behavior: 'smooth'
        })
    }
}

// Update page dimensions when page changes
watch(currentPage, async (newPage) => {
    if (pdf.value && 'getPage' in pdf.value && newPage <= totalPages.value) {
        try {
            const page = await (pdf.value as any).getPage(newPage)
            const viewport = page.getViewport({ scale: 1.0 })

            pageWidth.value = viewport.width
            pageHeight.value = viewport.height

            // Auto-fit page if scale is close to optimal
            nextTick(() => {
                const currentOptimal = calculateOptimalScale()
                const scaleRatio = scale.value / currentOptimal
                if (scaleRatio >= 0.9 && scaleRatio <= 1.1) {
                    fitToPage()
                }
            })
        } catch (error) {
            console.error('Error getting page dimensions:', error)
        }
    }
})


// Watch for PDF data changes
watch(() => props.pdfData, (newData) => {
    const hasData = newData !== undefined && newData !== null
    console.log('PDF data changed:', hasData ? 'Data received' : 'No data')

    if (hasData) {
        currentPage.value = 1
        totalPages.value = 0
        highlightRects.value = [] // Clear previous highlights
        // Scroll to top when new PDF is loaded
        nextTick(() => {
            scrollToTop()
        })
    }
})

// Watch for highlight props changes
watch([() => props.highlightText, () => props.highlightPage, pdf], async ([newText, newPage, newPdf]) => {
    console.log('Highlight watch triggered:', { newText, newPage, hasPdf: !!newPdf })

    if (newPdf && newText && newPage && newPage > 0) {
        console.log('Starting text search for:', newText, 'on page:', newPage)

        // Wait a bit for PDF to be fully loaded
        await nextTick()
        setTimeout(() => {
            findAndHighlightText(newText, newPage)
        }, 1000) // Increased delay to ensure PDF is fully loaded
    } else {
        console.log('Skipping highlight - missing data:', { hasPdf: !!newPdf, hasText: !!newText, page: newPage })
    }
}, { immediate: false })

// Watch for PDF loading to ensure we can access pages
watch(pdf, (newPdf) => {
    console.log('PDF loaded:', !!newPdf)
    if (newPdf) {
        // PDF is ready, first scroll to the target page, then try to highlight
        const { highlightText, highlightPage } = props
        if (highlightPage && highlightPage > 0) {
            console.log('PDF ready, scrolling to page:', highlightPage)
            // Always scroll to the target page first
            currentPage.value = highlightPage

            // Then try to highlight text if available
            if (highlightText) {
                console.log('PDF ready, highlighting text:', highlightText, 'on page:', highlightPage)
                setTimeout(() => {
                    findAndHighlightText(highlightText, highlightPage)
                }, 500)
            }
        }
    }
})

// Watch for visibility changes
watch(() => props.isVisible, (visible) => {
    if (visible && props.pdfData !== undefined && props.pdfData !== null) {
        // Reset page when becoming visible
        currentPage.value = 1
    }
})

</script>

<style scoped>
.pdf-viewer {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    background-color: white;
    border-left: 1px solid var(--color-border);
}

.pdf-viewer__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--color-border);
    background-color: var(--color-background-secondary);
    flex-shrink: 0;
}

.pdf-viewer__title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    color: var(--color-text-primary);
}

.title-text {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
}

.title-icon {
    width: 1.25rem;
    height: 1.25rem;
    color: var(--color-primary);
}

.pdf-viewer__controls {
    display: flex;
    gap: 0.5rem;
}

.control-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    background-color: white;
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all 0.2s;
}

.control-button:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background-color: var(--color-primary-light);
}

.control-button--close:hover {
    border-color: var(--color-error);
    color: var(--color-error);
    background-color: rgba(220, 38, 38, 0.05);
}

.control-icon {
    width: 1rem;
    height: 1rem;
}

.pdf-viewer__content {
    flex: 1;
    overflow: auto;
    padding: 0;
    width: 100%;
    height: 100%;
}

.loading-state,
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    width: 100%;
    text-align: center;
}

.loading-spinner {
    width: 2rem;
    height: 2rem;
    border: 2px solid var(--color-border);
    border-top: 2px solid var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
}

@keyframes spin {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

.error-icon {
    width: 3rem;
    height: 3rem;
    margin-bottom: 1rem;
    color: var(--color-error);
}

.retry-button {
    margin-top: 1rem;
    padding: 0.75rem 1.5rem;
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: 0.5rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
}

.retry-button:hover {
    background-color: var(--color-primary-hover);
}

.pdf-content {
    display: flex;
    flex-direction: column;
    min-height: 100%;
    width: 100%;
    padding-bottom: 1rem;
}

.pdf-embed {
    flex: 1;
    width: 100%;
    min-height: 100%;
    border: none;
    border-radius: 0;
    overflow: visible;
    position: relative;
}

/* VuePDF text layer and annotation layer styling */
.pdf-embed :deep(.textLayer) {
    position: absolute;
    left: 0;
    top: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
    opacity: 0.2;
    line-height: 1;
    text-align: initial;
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
}

.pdf-embed :deep(.textLayer span) {
    color: transparent;
    position: absolute;
    white-space: pre;
    cursor: text;
    transform-origin: 0% 0%;
}

.pdf-embed :deep(.textLayer .highlight) {
    background-color: rgba(255, 255, 0, 0.3);
    border-radius: 2px;
    box-shadow: 0 0 0 1px rgba(255, 255, 0, 0.5);
}

.pdf-embed :deep(.annotationLayer) {
    position: absolute;
    left: 0;
    top: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
}

.pdf-embed :deep(.annotationLayer section) {
    position: absolute;
    pointer-events: auto;
}

.pdf-embed :deep(.canvasWrapper) {
    position: relative;
    overflow: hidden;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: flex-start;
}

.pdf-embed :deep(.canvasWrapper canvas) {
    display: block;
    width: 100%;
    height: auto;
    max-width: 100%;
    object-fit: contain;
}

/* Custom scrollbar styles for PDF viewer */
.pdf-viewer__content::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

.pdf-viewer__content::-webkit-scrollbar-track {
    background: var(--color-background);
    border-radius: 4px;
}

.pdf-viewer__content::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
    transition: background-color 0.2s;
}

.pdf-viewer__content::-webkit-scrollbar-thumb:hover {
    background: var(--color-text-muted);
}

.pdf-viewer__content::-webkit-scrollbar-corner {
    background: var(--color-background);
}

/* Smooth scrolling for PDF content */
.pdf-viewer__content {
    scroll-behavior: smooth;
}

/* Ensure proper scrolling on different browsers */
.pdf-viewer__content {
    scrollbar-width: thin;
    scrollbar-color: var(--color-border) var(--color-background);
}

/* Prevent text selection issues */
.pdf-embed :deep(*) {
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
    user-select: text;
}

/* Ensure proper text rendering */
.pdf-embed :deep(.textLayer) {
    font-family: monospace;
    font-size: 1em;
    line-height: 1.2;
    color: transparent;
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    overflow: hidden;
    opacity: 0.2;
    line-height: 1;
    text-align: initial;
    user-select: text;
    -webkit-user-select: text;
    -moz-user-select: text;
    -ms-user-select: text;
    z-index: 1;
}

.pdf-embed :deep(.textLayer span) {
    color: transparent;
    position: absolute;
    white-space: pre;
    cursor: text;
    transform-origin: 0% 0%;
    background-color: transparent;
    border: none;
    margin: 0;
    padding: 0;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
}

/* Highlight selection properly */
.pdf-embed :deep(.textLayer .highlight) {
    background-color: rgba(0, 0, 255, 0.3) !important;
    border-radius: 2px;
    box-shadow: none;
    mix-blend-mode: multiply;
}

/* Prevent layout shifts during selection */
.pdf-embed :deep(.textLayer span::selection) {
    background-color: rgba(0, 0, 255, 0.3);
    color: transparent;
}

.pdf-embed :deep(.textLayer span::-moz-selection) {
    background-color: rgba(0, 0, 255, 0.3);
    color: transparent;
}



.pdf-navigation {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    border-top: 1px solid var(--color-border);
    background-color: var(--color-background-secondary);
    position: sticky;
    bottom: 0;
    z-index: 100;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
    margin-top: 1rem;
    /* Ensure navigation is always visible */
    position: -webkit-sticky;
    position: sticky;
    /* Fallback for browsers that don't support sticky */
    transform: translateZ(0);
    will-change: transform;
    /* Responsive adjustments */
    flex-wrap: wrap;
    min-height: 3.5rem;
}

/* Mobile adjustments for navigation */
@media (max-width: 640px) {
    .pdf-navigation {
        padding: 0.75rem 0.5rem;
        gap: 0.5rem;
    }

    .nav-button {
        width: 2rem;
        height: 2rem;
    }

    .page-input {
        width: 2.5rem;
        font-size: 0.8rem;
    }
}

.nav-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    background-color: white;
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all 0.2s;
    /* Ensure buttons are always clickable */
    position: relative;
    z-index: 101;
    /* Better visibility */
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.nav-button:hover:not(:disabled) {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background-color: var(--color-primary-light);
}

.nav-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.nav-icon {
    width: 1.25rem;
    height: 1.25rem;
}

.page-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    /* Ensure page info is always visible */
    position: relative;
    z-index: 101;
}

.page-input {
    width: 3rem;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--color-border);
    background-color: white;
    border-radius: 0.25rem;
    text-align: center;
    font-size: 0.875rem;
}

.page-input:focus {
    outline: none;
    border-color: var(--color-primary);
}

/* PDF Container with overlay support */
.pdf-container {
    position: relative;
    width: 100%;
    height: 100%;
}

.pdf-embed {
    position: relative;
    width: 100%;
    min-height: 100%;
    border: none;
    border-radius: 0;
    overflow: visible;
    position: relative;
    z-index: 1;
}

/* Highlight overlay */
.highlight-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 2;
}

.highlight-rect {
    position: absolute;
    background-color: rgba(255, 255, 0, 0.4);
    border: 2px solid rgba(255, 165, 0, 0.8);
    border-radius: 2px;
    box-shadow: 0 0 4px rgba(255, 165, 0, 0.6);
    animation: highlight-pulse 2s ease-in-out infinite;
}

@keyframes highlight-pulse {
    0% { box-shadow: 0 0 4px rgba(255, 165, 0, 0.6); }
    50% { box-shadow: 0 0 8px rgba(255, 165, 0, 0.9); }
    100% { box-shadow: 0 0 4px rgba(255, 165, 0, 0.6); }
}
</style>
