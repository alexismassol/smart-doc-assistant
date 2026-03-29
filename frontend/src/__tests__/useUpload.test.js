/**
 * useUpload.test.js - Tests unitaires du hook useUpload
 * Uses: Vitest, React Testing Library (renderHook), fetch mock
 *
 * Matrice de conformité :
 * - Nominal : uploadFile succès, ingestUrl succès, deleteDoc succès
 * - Bornes : fetch erreur → retourne { success: false, error }
 * - Contrats : fetchHealth et fetchDocuments appelés au mount
 * - Idempotence : deleteDoc filtre uniquement le bon doc
 */
import { renderHook, act, waitFor } from '@testing-library/react'
import { useUpload } from '../hooks/useUpload.js'

const mockDocuments = [
  { source: 'api.pdf', type: 'pdf', chunk_count: 12 },
  { source: 'data.csv', type: 'csv', chunk_count: 5 },
]

const mockHealth = {
  status: 'ok',
  llm_provider: 'ollama',
  documents_count: 17,
}

function setupFetchMock({ docs = mockDocuments, health = mockHealth, uploadChunks = 8 } = {}) {
  global.fetch = vi.fn().mockImplementation((url, opts) => {
    if (url === '/api/health') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(health) })
    }
    if (url === '/api/documents' && (!opts || opts.method !== 'DELETE')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ documents: docs }) })
    }
    if (url === '/api/upload') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ chunks_created: uploadChunks, source: 'test.pdf' }),
      })
    }
    if (url === '/api/ingest-url') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ chunks_created: 5, source: 'https://example.com' }),
      })
    }
    if (url?.includes('/api/documents/') && opts?.method === 'DELETE') {
      return Promise.resolve({ ok: true })
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Not found' }) })
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useUpload - initialisation', () => {
  it('charge les documents au mount', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.documents).toHaveLength(2))
  })

  it('charge la santé du serveur au mount', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.health?.llm_provider).toBe('ollama'))
  })

  it('isUploading est false au démarrage', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    // Attendre la fin des fetches initiaux avant assertion
    await waitFor(() => expect(result.current.documents).toBeDefined())
    expect(result.current.isUploading).toBe(false)
  })
})

describe('useUpload - uploadFile', () => {
  it('retourne { success: true, chunks } après upload réussi', async () => {
    setupFetchMock({ uploadChunks: 8 })
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.documents).toHaveLength(2))

    let uploadResult
    await act(async () => {
      const file = new File(['contenu test'], 'test.pdf', { type: 'application/pdf' })
      uploadResult = await result.current.uploadFile(file)
    })
    expect(uploadResult.success).toBe(true)
    expect(uploadResult.chunks).toBe(8)
  })

  it('retourne { success: false, error } si erreur serveur', async () => {
    setupFetchMock()
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url === '/api/health') return Promise.resolve({ ok: true, json: () => Promise.resolve(mockHealth) })
      if (url === '/api/documents') return Promise.resolve({ ok: true, json: () => Promise.resolve({ documents: [] }) })
      if (url === '/api/upload') return Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'Format non supporté' }),
      })
      return Promise.resolve({ ok: false, json: () => Promise.resolve({}) })
    })
    const { result } = renderHook(() => useUpload())
    let uploadResult
    await act(async () => {
      const file = new File(['x'], 'test.exe', { type: 'application/x-msdownload' })
      uploadResult = await result.current.uploadFile(file)
    })
    expect(uploadResult.success).toBe(false)
    expect(uploadResult.error).toBe('Format non supporté')
  })

  it('isUploading repasse à false après upload', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await act(async () => {
      const file = new File(['x'], 'test.pdf', { type: 'application/pdf' })
      await result.current.uploadFile(file)
    })
    expect(result.current.isUploading).toBe(false)
  })
})

describe('useUpload - ingestUrl', () => {
  it('retourne { success: true, chunks } après ingest URL réussi', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.documents).toHaveLength(2))

    let ingestResult
    await act(async () => {
      ingestResult = await result.current.ingestUrl('https://example.com')
    })
    expect(ingestResult.success).toBe(true)
    expect(ingestResult.chunks).toBe(5)
  })
})

describe('useUpload - deleteDoc', () => {
  it('retire le document de la liste localement', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.documents).toHaveLength(2))

    await act(async () => {
      await result.current.deleteDoc('api.pdf')
    })
    expect(result.current.documents.find(d => d.source === 'api.pdf')).toBeUndefined()
    expect(result.current.documents).toHaveLength(1)
  })

  it('ne retire que le bon document (idempotence)', async () => {
    setupFetchMock()
    const { result } = renderHook(() => useUpload())
    await waitFor(() => expect(result.current.documents).toHaveLength(2))

    await act(async () => {
      await result.current.deleteDoc('api.pdf')
    })
    expect(result.current.documents[0].source).toBe('data.csv')
  })
})
