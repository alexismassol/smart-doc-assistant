/**
 * useChat.test.js - Tests unitaires du hook useChat (streaming SSE)
 * Uses: Vitest, React Testing Library (renderHook), fetch mock (ReadableStream)
 *
 * Matrice de conformité :
 * - Nominal    : sendMessage → stream SSE → tokens accumulés → sources/done
 * - Bornes     : question vide/undefined/whitespace → pas d'appel fetch
 * - Erreurs    : fetch fail → message erreur, fetch 500 → message erreur
 * - Contrats   : sessionId stable (UUID), reset vide les messages
 * - Métadonnées: lastLatency défini après réponse réussie
 */
import { renderHook, act, waitFor } from '@testing-library/react'
import { useChat } from '../hooks/useChat.js'

// ── Helpers SSE mock ───────────────────────────────────────────────────────────

/**
 * Crée un mock fetch qui retourne un ReadableStream SSE.
 * @param {string[]} tokens - Tokens à streamer
 * @param {Object} sourcesPayload - Payload de l'événement sources
 */
function mockStreamFetch(tokens = ['Bonjour', ' monde'], sourcesPayload = {
  sources: [{ source: 'api.pdf', content: 'Rate limit', score: 0.87, type: 'pdf', page: 1 }],
  confidence: 0.87,
  session_id: 'abc123',
}) {
  const lines = [
    ...tokens.map(t => `data: ${JSON.stringify({ type: 'token', content: t })}\n\n`),
    `data: ${JSON.stringify({ type: 'sources', ...sourcesPayload })}\n\n`,
    `data: ${JSON.stringify({ type: 'done' })}\n\n`,
  ]
  const fullText = lines.join('')
  const encoder = new TextEncoder()
  const encoded = encoder.encode(fullText)

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoded)
      controller.close()
    },
  })

  return vi.fn().mockResolvedValue({
    ok: true,
    body: stream,
  })
}

// ── Initialisation ─────────────────────────────────────────────────────────────

describe('useChat - initialisation', () => {
  it('commence avec une liste de messages vide', () => {
    const { result } = renderHook(() => useChat())
    expect(result.current.messages).toEqual([])
  })

  it('isLoading est false au démarrage', () => {
    const { result } = renderHook(() => useChat())
    expect(result.current.isLoading).toBe(false)
  })

  it('sessionId est un UUID non vide', () => {
    const { result } = renderHook(() => useChat())
    expect(result.current.sessionId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
    )
  })

  it('lastLatency est null au démarrage', () => {
    const { result } = renderHook(() => useChat())
    expect(result.current.lastLatency).toBeNull()
  })
})

// ── sendMessage nominal (streaming) ───────────────────────────────────────────

describe('useChat - sendMessage nominal (stream SSE)', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('ajoute le message utilisateur immédiatement', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Ma question')
    })
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[0].content).toBe('Ma question')
  })

  it('appelle fetch /api/chat/stream avec la bonne question', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Ma question')
    })
    expect(global.fetch).toHaveBeenCalledWith('/api/chat/stream', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }))
    const body = JSON.parse(global.fetch.mock.calls[0][1].body)
    expect(body.question).toBe('Ma question')
  })

  it('accumule les tokens dans le message assistant', async () => {
    global.fetch = mockStreamFetch(['La ', 'limite ', 'est ', '100.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Quelle est la limite ?')
    })
    await waitFor(() => {
      const assistant = result.current.messages.find(m => m.role === 'assistant')
      expect(assistant?.content).toBe('La limite est 100.')
    })
  })

  it('le message assistant a 2 messages au total (user + assistant)', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
    })
  })

  it('isStreaming est false après la fin du stream', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    await waitFor(() => {
      const assistant = result.current.messages.find(m => m.role === 'assistant')
      expect(assistant?.isStreaming).toBe(false)
    })
  })

  it('sources sont renseignées après l\'événement sources', async () => {
    global.fetch = mockStreamFetch(['Réponse.'], {
      sources: [{ source: 'doc.pdf', content: 'x', score: 0.9, type: 'pdf', page: 1 }],
      confidence: 0.9,
      session_id: 'test',
    })
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    await waitFor(() => {
      const assistant = result.current.messages.find(m => m.role === 'assistant')
      expect(assistant?.sources).toHaveLength(1)
      expect(assistant?.confidence).toBe(0.9)
    })
  })

  it('stocke une latence positive après une réponse réussie', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    await waitFor(() => {
      expect(result.current.lastLatency).toBeGreaterThanOrEqual(0)
    })
  })

  it('isLoading repasse à false après la réponse', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => {
      await result.current.sendMessage('Question')
    })
    expect(result.current.isLoading).toBe(false)
  })
})

// ── Bornes (inputs invalides) ──────────────────────────────────────────────────

describe('useChat - bornes (inputs invalides)', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('question vide → fetch non appelé', async () => {
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('') })
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('question undefined → fetch non appelé', async () => {
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage(undefined) })
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('question whitespace seul → fetch non appelé', async () => {
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('   ') })
    expect(global.fetch).not.toHaveBeenCalled()
  })
})

// ── Erreurs réseau ─────────────────────────────────────────────────────────────

describe('useChat - erreur réseau', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetch rejet → message erreur ajouté', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('Question') })
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2)
      expect(result.current.messages[1].isError).toBe(true)
    })
  })

  it('fetch 500 → message erreur ajouté', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, body: null })
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('Question') })
    await waitFor(() => {
      expect(result.current.messages[1].isError).toBe(true)
    })
  })
})

// ── Reset ──────────────────────────────────────────────────────────────────────

describe('useChat - reset', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reset vide les messages', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('Question') })
    await waitFor(() => expect(result.current.messages).toHaveLength(2))
    act(() => result.current.reset())
    expect(result.current.messages).toHaveLength(0)
  })

  it('reset remet lastLatency à null', async () => {
    global.fetch = mockStreamFetch(['Réponse.'])
    const { result } = renderHook(() => useChat())
    await act(async () => { await result.current.sendMessage('Question') })
    await waitFor(() => expect(result.current.lastLatency).not.toBeNull())
    act(() => result.current.reset())
    expect(result.current.lastLatency).toBeNull()
  })
})
