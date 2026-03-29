/**
 * StatusBar - Barre de statut en haut de l'interface
 * Affiche : LLM actif | docs indexés | dernière latence
 */
export default function StatusBar({ llmProvider, documentsCount, latency }) {
  const providerLabel = {
    ollama: '⚡ Ollama local',
    mistral: '🌐 Mistral API',
    anthropic: '🤖 Claude',
  }[llmProvider] || '- Connexion...'

  return (
    <div className="flex items-center justify-between px-6 py-2.5 border-b border-border bg-surface/50 backdrop-blur-sm">
      {/* Logo + nom */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center shadow-glow-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-white">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span className="hidden md:inline text-sm font-semibold text-text tracking-tight">Smart Doc Assistant</span>
      </div>

      {/* Métriques */}
      <div className="flex items-center gap-5">
        <Metric
          icon={<DotIcon color={llmProvider ? '#10b981' : '#525252'} />}
          label={providerLabel}
        />
        <div className="w-px h-3.5 bg-border" />
        <Metric
          icon={<DocIcon />}
          label={`${documentsCount ?? 0} chunk${documentsCount !== 1 ? 's' : ''}`}
        />
        {latency != null && (
          <>
            <div className="w-px h-3.5 bg-border" />
            <Metric icon={<ClockIcon />} label={`${latency} ms`} />
          </>
        )}
      </div>
    </div>
  )
}

function Metric({ icon, label }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-text-secondary">
      {icon}
      <span>{label}</span>
    </div>
  )
}

function DotIcon({ color }) {
  return <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ background: color, boxShadow: color !== '#525252' ? `0 0 6px ${color}` : 'none' }} />
}

function DocIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="text-text-dim">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
      <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2"/>
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="text-text-dim">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
      <polyline points="12,6 12,12 16,14" stroke="currentColor" strokeWidth="2"/>
    </svg>
  )
}
