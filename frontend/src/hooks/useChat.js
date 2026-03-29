import { useState, useCallback } from 'react'

/**
 * useChat - Gestion de la conversation avec l'agent RAG
 * Uses: fetch API (ReadableStream) → POST /api/chat/stream (SSE token-by-token)
 *
 * Streaming SSE - 3 types d'événements reçus :
 *   { type: "token",   content: "La " }           → accumulation token par token
 *   { type: "sources", sources: [...], confidence, session_id }
 *   { type: "done" }                               → fin du stream
 */
export function useChat() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
  const [lastLatency, setLastLatency] = useState(null)

  const sendMessage = useCallback(async (question) => {
    if (!question?.trim() || isLoading) return

    // Ajout immédiat du message utilisateur
    const userMessage = { role: 'user', content: question, id: Date.now() }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    // L'assistant placeholder sera ajouté au premier token reçu
    const assistantId = Date.now() + 1
    let assistantAdded = false

    const startTime = Date.now()

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim(), session_id: sessionId }),
      })

      if (!response.ok) throw new Error(`Erreur ${response.status}`)

      // ── Lecture du stream SSE via ReadableStream ───────────────────────────
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // garder la ligne incomplète pour le prochain chunk

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

            if (event.type === 'token') {
              // Premier token : créer la bulle assistant et cacher le TypingIndicator
              if (!assistantAdded) {
                assistantAdded = true
                setIsLoading(false)
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: event.content,
                  sources: [],
                  confidence: 0,
                  isStreaming: true,
                  id: assistantId,
                }])
              } else {
                // Tokens suivants : accumulation
                setMessages(prev => prev.map(msg =>
                  msg.id === assistantId
                    ? { ...msg, content: msg.content + event.content }
                    : msg
                ))
              }

            } else if (event.type === 'sources') {
              // Mise à jour sources + confidence + fin de streaming
              const latency = Date.now() - startTime
              setLastLatency(latency)
              setMessages(prev => prev.map(msg =>
                msg.id === assistantId
                  ? { ...msg, sources: event.sources, confidence: event.confidence,
                      latency_ms: latency, isStreaming: false }
                  : msg
              ))

            } else if (event.type === 'done') {
              // S'assurer que isStreaming est false
              setMessages(prev => prev.map(msg =>
                msg.id === assistantId ? { ...msg, isStreaming: false } : msg
              ))
            }
          } catch {
            // Ligne SSE malformée - on ignore
          }
        }
      }
    } catch (err) {
      // Si aucun token reçu, ajouter quand même une bulle d'erreur
      if (!assistantAdded) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Erreur de connexion au serveur. Vérifiez que le backend est démarré.',
          sources: [],
          confidence: 0,
          isError: true,
          isStreaming: false,
          id: assistantId,
        }])
      } else {
        setMessages(prev => prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: 'Erreur de connexion au serveur.', isError: true, isStreaming: false }
            : msg
        ))
      }
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId])

  const reset = useCallback(() => {
    setMessages([])
    setSessionId(crypto.randomUUID())
    setLastLatency(null)
  }, [])

  // Charger une session existante depuis l'historique SQLite
  const loadSession = useCallback(async (targetSessionId) => {
    try {
      const res = await fetch(`/api/history/${targetSessionId}`)
      if (!res.ok) return
      const data = await res.json()
      const loaded = data.messages.map((m, i) => ({
        role: m.role,
        content: m.content,
        id: i,
        // sources et confidence non stockés en SQLite - null = pas d'affichage de métriques
        sources: [],
        confidence: null,
        isStreaming: false,
      }))
      setMessages(loaded)
      setSessionId(targetSessionId)
      setLastLatency(null)
    } catch {
      // Silencieux - session non chargée
    }
  }, [])

  return { messages, isLoading, sendMessage, reset, loadSession, lastLatency, sessionId }
}
