import { useState, useRef, useEffect } from 'react'

/**
 * UploadPanel - Panneau gauche : drag & drop + liste des documents + historique conversations
 * Sur mobile : collapsible via header cliquable
 */
export default function UploadPanel({ documents, isUploading, onUploadFile, onIngestUrl, onDeleteDoc, onLoadSession, activeSessionId }) {
  const [sessions, setSessions] = useState([])

  // Charger la liste des sessions depuis SQLite
  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.ok ? r.json() : { sessions: [] })
      .then(data => setSessions(data.sessions ?? []))
      .catch(() => {})
  }, [activeSessionId]) // Recharger quand on change de session (nouvelle conv créée)
  const [isDragging, setIsDragging] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [feedback, setFeedback] = useState(null) // { type: 'success'|'error', message }
  const [mobileOpen, setMobileOpen] = useState(false)
  const fileInputRef = useRef(null)

  const showFeedback = (type, message) => {
    setFeedback({ type, message })
    setTimeout(() => setFeedback(null), 3000)
  }

  const handleFile = async (file) => {
    if (!file) return
    const result = await onUploadFile(file)
    if (result.success) {
      showFeedback('success', `${file.name} - ${result.chunks} chunks indexés`)
    } else {
      showFeedback('error', result.error)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleUrlSubmit = async (e) => {
    e.preventDefault()
    if (!urlInput.trim()) return
    const result = await onIngestUrl(urlInput.trim())
    if (result.success) {
      showFeedback('success', `URL indexée - ${result.chunks} chunks`)
      setUrlInput('')
    } else {
      showFeedback('error', result.error)
    }
  }

  return (
    <aside className={`w-full md:w-80 flex-none flex flex-col border-b md:border-b-0 md:border-r border-border bg-surface/30 overflow-hidden transition-all duration-200 ${mobileOpen ? 'flex-1' : 'h-auto'} md:flex-1 md:h-auto`}>
      {/* Header - cliquable sur mobile pour expand/collapse */}
      <div className="px-5 pt-5 pb-4">
        <button
          className="w-full flex items-center justify-between mb-4 md:cursor-default"
          onClick={() => setMobileOpen(o => !o)}
        >
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-widest">
            Documents {documents.length > 0 && <span className="text-accent">({documents.length})</span>}
          </h2>
          {/* Chevron visible uniquement sur mobile */}
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none"
            className={`md:hidden text-text-dim transition-transform duration-200 ${mobileOpen ? 'rotate-180' : ''}`}
          >
            <polyline points="6,9 12,15 18,9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        {/* Contenu masqué sur mobile si collapsed */}
        <div className={`${mobileOpen ? 'block' : 'hidden'} md:block`}>

        {/* Drop zone */}
        <div
          className={`relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-150 ${
            isDragging
              ? 'border-accent bg-accent-dim shadow-glow-sm'
              : 'border-border-bright hover:border-accent/50 hover:bg-elevated'
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.csv,.md,.txt"
            onChange={(e) => handleFile(e.target.files[0])}
          />

          {isUploading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-text-secondary">Indexation...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <div className="w-10 h-10 rounded-xl bg-elevated border border-border-bright flex items-center justify-center mb-1">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="text-text-secondary">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <polyline points="17,8 12,3 7,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <p className="text-xs font-medium text-text">Déposer un fichier</p>
              <p className="text-xs text-text-dim">PDF · CSV · MD · TXT</p>
            </div>
          )}
        </div>

        {/* Feedback toast */}
        {feedback && (
          <div className={`mt-3 px-3 py-2 rounded-lg text-xs animate-fade-in ${
            feedback.type === 'success'
              ? 'bg-success/10 text-success border border-success/20'
              : 'bg-error/10 text-error border border-error/20'
          }`}>
            {feedback.message}
          </div>
        )}

        {/* URL ingestion */}
        <form onSubmit={handleUrlSubmit} className="mt-4">
          <div className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://..."
              className="flex-1 bg-elevated border border-border-bright rounded-lg px-3 py-2 text-xs text-text placeholder-text-dim input-glow transition-all duration-150"
            />
            <button
              type="submit"
              disabled={!urlInput.trim() || isUploading}
              className="px-3 py-2 bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-xs font-medium text-white transition-all duration-150"
            >
              +
            </button>
          </div>
        </form>

        </div>{/* fin contenu mobile collapsible */}
      </div>

      {/* Zone scrollable : documents + conversations - masquée sur mobile si collapsed */}
      <div className={`overflow-y-auto flex-1 px-5 pb-5 ${mobileOpen ? 'block' : 'hidden'} md:block`}>

        {/* Liste des documents */}
        {documents.length === 0 ? (
          <div className="text-center py-4">
            <p className="text-xs text-text-dim">Aucun document indexé</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentItem key={doc.source} doc={doc} onDelete={onDeleteDoc} />
            ))}
          </div>
        )}

        {/* Séparateur + section conversations */}
        <div className="border-t border-border mt-4 pt-4">
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-widest mb-3">
            Conversations {sessions.length > 0 && <span className="text-accent">({sessions.length})</span>}
          </h2>
          {sessions.length === 0 ? (
            <p className="text-xs text-text-dim text-center py-2">Aucune conversation</p>
          ) : (
            <div className="space-y-1.5">
              {sessions.map((s) => (
                <SessionItem
                  key={s.session_id}
                  session={s}
                  isActive={s.session_id === activeSessionId}
                  onLoad={onLoadSession}
                />
              ))}
            </div>
          )}
        </div>

      </div>
    </aside>
  )
}

function SessionItem({ session, isActive, onLoad }) {
  const date = new Date(session.last_message_at)
  const label = date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })
    + ' ' + date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })

  return (
    <button
      onClick={() => onLoad(session.session_id)}
      className={`w-full text-left px-3 py-2 rounded-lg border transition-all duration-150 ${
        isActive
          ? 'bg-accent/10 border-accent/40 text-accent'
          : 'bg-elevated border-border hover:border-border-bright text-text'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs truncate">{label}</span>
        <span className="text-xs text-text-dim flex-none">{session.message_count} msg</span>
      </div>
    </button>
  )
}

function DocumentItem({ doc, onDelete }) {
  const typeColors = {
    pdf: 'text-error',
    csv: 'text-success',
    markdown: 'text-accent',
    url: 'text-warning',
    txt: 'text-text-secondary',
  }

  return (
    <div className="group flex items-center justify-between px-3 py-2.5 rounded-lg bg-elevated border border-border hover:border-border-bright transition-all duration-150">
      <div className="flex items-center gap-2.5 min-w-0">
        <span className={`text-xs font-mono font-semibold uppercase ${typeColors[doc.type] || 'text-text-secondary'}`}>
          {doc.type?.slice(0, 3) || '?'}
        </span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-text truncate max-w-[140px]">{doc.source}</p>
          <p className="text-xs text-text-dim">{doc.chunk_count} chunks</p>
        </div>
      </div>
      <button
        onClick={() => onDelete(doc.source)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded text-text-dim hover:text-error transition-all duration-150"
        title="Supprimer"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </button>
    </div>
  )
}
