/**
 * MessageBubble.test.jsx — Tests unitaires du composant MessageBubble
 * Uses: Vitest, React Testing Library
 *
 * Matrice de conformité :
 * - Nominal : message user, message assistant avec sources
 * - Bornes : 0 source, 1 source, N sources, confidence 0/0.4/0.7/1
 * - Erreurs : isError flag → style erreur
 * - Métadonnées : latency_ms affiché, confidence colorée
 */
import { render, screen } from '@testing-library/react'
import MessageBubble from '../components/MessageBubble.jsx'

const userMessage = { role: 'user', content: 'Quelle est la limite de taux ?', id: 1 }

const assistantMessage = {
  role: 'assistant',
  content: 'La limite est de 100 req/min.',
  sources: [{ source: 'api.pdf', content: 'Rate limit 100/min', score: 0.87, type: 'pdf', page: 5 }],
  confidence: 0.87,
  latency_ms: 1240,
  id: 2,
}

describe('MessageBubble — message utilisateur', () => {
  it('affiche le contenu du message', () => {
    render(<MessageBubble message={userMessage} />)
    expect(screen.getByText('Quelle est la limite de taux ?')).toBeInTheDocument()
  })

  it('ne montre pas les sources pour un message utilisateur', () => {
    render(<MessageBubble message={userMessage} />)
    expect(screen.queryByText(/source/i)).not.toBeInTheDocument()
  })

  it('ne montre pas la confiance pour un message utilisateur', () => {
    render(<MessageBubble message={userMessage} />)
    expect(screen.queryByText(/confiance/i)).not.toBeInTheDocument()
  })
})

describe('MessageBubble — message assistant', () => {
  it('affiche la réponse de l\'assistant', () => {
    render(<MessageBubble message={assistantMessage} />)
    expect(screen.getByText('La limite est de 100 req/min.')).toBeInTheDocument()
  })

  it('affiche le score de confiance', () => {
    render(<MessageBubble message={assistantMessage} />)
    expect(screen.getByText(/Confiance/i)).toBeInTheDocument()
    // 87% apparaît aussi dans SourceCard — on vérifie qu'au moins un élément est present
    expect(screen.getAllByText('87%').length).toBeGreaterThanOrEqual(1)
  })

  it('affiche la latence en ms', () => {
    render(<MessageBubble message={assistantMessage} />)
    expect(screen.getByText(/1240 ms/)).toBeInTheDocument()
  })

  it('affiche le nombre de sources', () => {
    render(<MessageBubble message={assistantMessage} />)
    expect(screen.getByText(/1 source utilisée/)).toBeInTheDocument()
  })
})

describe('MessageBubble — sources', () => {
  it('sans sources — pas de section sources', () => {
    const msg = { ...assistantMessage, sources: [] }
    render(<MessageBubble message={msg} />)
    expect(screen.queryByText(/source/)).not.toBeInTheDocument()
  })

  it('pluriel pour plusieurs sources', () => {
    const src = { source: 'x.pdf', content: 'foo', score: 0.5, type: 'pdf', page: 1 }
    const msg = { ...assistantMessage, sources: [src, src] }
    render(<MessageBubble message={msg} />)
    expect(screen.getByText(/2 sources utilisées/)).toBeInTheDocument()
  })
})

describe('MessageBubble — confiance colorée', () => {
  it('confidence >= 0.7 → texte success', () => {
    const msg = { ...assistantMessage, confidence: 0.7, sources: [] }
    const { container } = render(<MessageBubble message={msg} />)
    expect(container.querySelector('.text-success')).toBeInTheDocument()
  })

  it('confidence 0.5 (entre 0.4 et 0.7) → texte warning', () => {
    const msg = { ...assistantMessage, confidence: 0.5, sources: [] }
    const { container } = render(<MessageBubble message={msg} />)
    expect(container.querySelector('.text-warning')).toBeInTheDocument()
  })

  it('confidence < 0.4 → texte dim', () => {
    const msg = { ...assistantMessage, confidence: 0.2, sources: [] }
    const { container } = render(<MessageBubble message={msg} />)
    // The span has text-text-dim class when confidence < 0.4
    const spans = container.querySelectorAll('.text-text-dim')
    expect(spans.length).toBeGreaterThan(0)
  })
})

describe('MessageBubble — erreur', () => {
  it('isError → style rouge affiché', () => {
    const msg = { role: 'assistant', content: 'Erreur de connexion', isError: true, sources: [], id: 3 }
    const { container } = render(<MessageBubble message={msg} />)
    expect(container.querySelector('.text-error')).toBeInTheDocument()
  })

  it('isError → pas de section confiance', () => {
    const msg = { role: 'assistant', content: 'Erreur', isError: true, sources: [], confidence: 0, id: 3 }
    render(<MessageBubble message={msg} />)
    expect(screen.queryByText(/Confiance/i)).not.toBeInTheDocument()
  })
})
