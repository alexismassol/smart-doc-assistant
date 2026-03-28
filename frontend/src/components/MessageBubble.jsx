import { useState } from 'react'
import SourceCard from './SourceCard.jsx'

/**
 * MessageBubble — Bulle de message (user ou assistant) avec sources optionnelles
 * Bouton "Copier" sur les bulles assistant (hors streaming)
 */
export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className={`flex animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1.5`}>
        {/* Bulle principale */}
        <div className={`relative group px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-accent text-white rounded-tr-sm shadow-glow-sm'
            : message.isError
              ? 'bg-error/10 text-error border border-error/20 rounded-tl-sm'
              : 'bg-elevated border border-border-bright text-text rounded-tl-sm'
        }`}>
          {message.content}
          {/* Curseur clignotant pendant le streaming */}
          {message.isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-accent ml-0.5 animate-pulse align-middle" />
          )}
          {/* Bouton copier — uniquement sur les bulles assistant terminées */}
          {!isUser && !message.isStreaming && message.content && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-border text-text-dim hover:text-text-secondary"
              title="Copier la réponse"
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
          )}
        </div>

        {/* Métriques pour les réponses assistant */}
        {!isUser && !message.isError && message.confidence != null && (
          <div className="flex items-center gap-3 px-1">
            <span className="text-xs text-text-dim">
              Confiance : <span className={`font-medium ${
                message.confidence >= 0.7 ? 'text-success' :
                message.confidence >= 0.4 ? 'text-warning' : 'text-text-dim'
              }`}>{(message.confidence * 100).toFixed(0)}%</span>
            </span>
            {message.latency_ms && (
              <span className="text-xs text-text-dim">{message.latency_ms} ms</span>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && message.sources?.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-text-dim px-1 mt-1">
              {message.sources.length} source{message.sources.length > 1 ? 's' : ''} utilisée{message.sources.length > 1 ? 's' : ''}
            </p>
            {message.sources.map((src, i) => (
              <SourceCard key={i} source={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-success">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}
