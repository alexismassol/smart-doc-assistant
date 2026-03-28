import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble.jsx'

/**
 * ChatWindow — Zone principale de conversation
 * Gère : liste des messages, input, bouton envoi, typing indicator, auto-scroll
 */
export default function ChatWindow({ messages, isLoading, onSend, onReset }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll au dernier message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    onSend(input.trim())
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <main className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
      {/* Zone messages — padding-bottom pour ne pas coller à la barre d'input */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-6 pt-6 pb-4 space-y-5">
        {messages.length === 0 ? (
          <EmptyState onSend={onSend} />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Barre d'input */}
      <div className="px-6 pt-4 pb-8 border-t border-border flex-shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Posez une question sur vos documents..."
              rows={1}
              className="w-full resize-none bg-elevated border border-border-bright rounded-xl px-4 py-3 text-sm text-text placeholder-text-dim input-glow transition-all duration-150 max-h-24 overflow-y-auto"
              style={{ lineHeight: '1.5' }}
            />
          </div>

          <div className="flex gap-2">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={onReset}
                className="p-3 rounded-xl bg-elevated border border-border-bright text-text-dim hover:text-text hover:border-border transition-all duration-150"
                title="Nouvelle conversation"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <path d="M3 3v5h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            )}
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-3 rounded-xl bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all duration-150 shadow-glow-sm hover:shadow-glow"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <polygon points="22,2 15,22 11,13 2,9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          </div>
        </form>
        <p className="text-xs text-text-dim mt-2 px-1">
          Entrée pour envoyer · Shift+Entrée pour nouvelle ligne
        </p>
      </div>
    </main>
  )
}

function EmptyState({ onSend }) {
  const suggestions = [
    'Résume les points clés de ce document',
    'Quels formats de fichiers puis-je uploader ?',
    'Comment fonctionne le pipeline RAG ?',
  ]

  return (
    <div className="flex flex-col items-center justify-center min-h-full gap-6 py-8 animate-fade-in">
      {/* Icône centrale avec glow */}
      <div className="relative">
        <div className="w-20 h-20 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center shadow-glow">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-accent">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-success border-2 border-bg shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
      </div>

      <div className="text-center max-w-sm">
        <h2 className="text-xl font-semibold text-text mb-2">Smart Doc Assistant</h2>
        <p className="text-sm text-text-secondary leading-relaxed">
          Interrogez vos documents en langage naturel. Uploadez un fichier ou une URL, puis posez vos questions.
        </p>
      </div>

      {/* Suggestions cliquables */}
      <div className="w-full max-w-md space-y-2">
        <p className="text-xs text-text-dim text-center mb-3 uppercase tracking-widest">Suggestions</p>
        {suggestions.map((s, i) => (
          <SuggestionChip key={i} text={s} onSend={onSend} />
        ))}
      </div>
    </div>
  )
}

function SuggestionChip({ text, onSend }) {
  return (
    <button
      onClick={() => onSend(text)}
      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-elevated border border-border hover:border-accent/50 hover:bg-accent/5 cursor-pointer transition-all duration-150 group text-left"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-accent flex-shrink-0">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
      <span className="text-sm text-text-secondary group-hover:text-text transition-colors">{text}</span>
    </button>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-elevated border border-border-bright flex items-center gap-1.5">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}
