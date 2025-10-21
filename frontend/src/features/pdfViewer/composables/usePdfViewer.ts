import { ref, computed } from 'vue'

export interface PdfDocument {
  id: string
  title: string
  filename: string
  base64Data: string | Uint8Array
  mimetype: string
}

export const usePdfViewer = () => {
  const currentPdf = ref<PdfDocument | null>(null)
  const isViewerOpen = ref(false)

  const isPdfLoaded = computed(() => !!currentPdf.value && isViewerOpen.value)

  const openPdf = (document: PdfDocument) => {
    currentPdf.value = document
    isViewerOpen.value = true
  }

  const closePdf = () => {
    currentPdf.value = null
    isViewerOpen.value = false
  }

  const loadPdfFromApi = async (documentId: string): Promise<PdfDocument | null> => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
      const url = `${apiBaseUrl}/api/v1/documents/${documentId}/view`

      const response = await fetch(url)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Server error:', errorText)
        throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`)
      }

      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Server returned invalid response format')
      }

      const data = await response.json()

      if (!data.base64) {
        throw new Error('Invalid response: missing base64 data')
      }

      // VuePDF can handle base64 strings directly
      return {
        id: documentId,
        title: data.title || 'PDF Document',
        filename: data.filename || 'document.pdf',
        base64Data: data.base64,
        mimetype: data.mimetype || 'application/pdf'
      }
    } catch (error) {
      console.error('Error fetching PDF:', error)
      throw error
    }
  }

  return {
    currentPdf,
    isViewerOpen,
    isPdfLoaded,
    openPdf,
    closePdf,
    loadPdfFromApi
  }
}
