/**
 * SourceCard - Affiche un chunk source avec score de pertinence
 */
export default function SourceCard({ source }) {
  const scoreClass =
    source.score >= 0.75 ? 'score-high' :
    source.score >= 0.5  ? 'score-mid'  : 'score-low'

  const typeIcon = {
    pdf: '📄',
    csv: '📊',
    markdown: '📝',
    url: '🌐',
    txt: '📋',
  }[source.type] || '📄'

  return (
    <div className="mt-2 pl-3 border-l-2 border-accent/50 py-2 pr-3 rounded-r-lg bg-surface/50 animate-fade-in">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs">{typeIcon}</span>
          <span className="text-xs font-medium text-text-secondary truncate max-w-[140px]">
            {source.source}
          </span>
          {source.page > 0 && (
            <span className="text-xs text-text-dim">p.{source.page}</span>
          )}
        </div>
        <span className={`text-xs font-mono font-semibold px-1.5 py-0.5 rounded ${scoreClass}`}>
          {(source.score * 100).toFixed(0)}%
        </span>
      </div>
      <p className="text-xs text-text-dim leading-relaxed line-clamp-2">
        {source.content}
      </p>
    </div>
  )
}
