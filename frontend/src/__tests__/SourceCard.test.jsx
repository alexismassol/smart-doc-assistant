/**
 * SourceCard.test.jsx — Tests unitaires du composant SourceCard
 * Uses: Vitest, React Testing Library
 *
 * Matrice de conformité :
 * - Nominal : source complète avec score + content
 * - Bornes : score 0, score 1, score 0.5, page = 0 (caché)
 * - Métadonnées : affichage source name, type icon, contenu tronqué
 * - Contrats : classe score-high/mid/low selon seuils
 */
import { render, screen } from '@testing-library/react'
import SourceCard from '../components/SourceCard.jsx'

const makeSource = (overrides = {}) => ({
  source: 'api-doc.pdf',
  content: 'La limite de taux de l\'API est de 100 requêtes par minute.',
  score: 0.87,
  type: 'pdf',
  page: 3,
  ...overrides,
})

describe('SourceCard — nominal', () => {
  it('affiche le nom de la source', () => {
    render(<SourceCard source={makeSource()} />)
    expect(screen.getByText('api-doc.pdf')).toBeInTheDocument()
  })

  it('affiche le score en pourcentage', () => {
    render(<SourceCard source={makeSource({ score: 0.87 })} />)
    expect(screen.getByText('87%')).toBeInTheDocument()
  })

  it('affiche le contenu du chunk', () => {
    render(<SourceCard source={makeSource()} />)
    expect(screen.getByText(/La limite de taux/)).toBeInTheDocument()
  })

  it('affiche le numéro de page si page > 0', () => {
    render(<SourceCard source={makeSource({ page: 3 })} />)
    expect(screen.getByText('p.3')).toBeInTheDocument()
  })
})

describe('SourceCard — bornes (scores)', () => {
  it('score >= 0.75 → classe score-high', () => {
    const { container } = render(<SourceCard source={makeSource({ score: 0.75 })} />)
    expect(container.querySelector('.score-high')).toBeInTheDocument()
  })

  it('score 0.5 → classe score-mid', () => {
    const { container } = render(<SourceCard source={makeSource({ score: 0.5 })} />)
    expect(container.querySelector('.score-mid')).toBeInTheDocument()
  })

  it('score 0.3 → classe score-low', () => {
    const { container } = render(<SourceCard source={makeSource({ score: 0.3 })} />)
    expect(container.querySelector('.score-low')).toBeInTheDocument()
  })

  it('score 1.0 → 100%', () => {
    render(<SourceCard source={makeSource({ score: 1.0 })} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('score 0.0 → 0%', () => {
    render(<SourceCard source={makeSource({ score: 0.0 })} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})

describe('SourceCard — page', () => {
  it('ne montre pas la page si page = 0', () => {
    render(<SourceCard source={makeSource({ page: 0 })} />)
    expect(screen.queryByText(/p\.\d/)).not.toBeInTheDocument()
  })

  it('ne montre pas la page si page est undefined', () => {
    const src = makeSource()
    delete src.page
    render(<SourceCard source={src} />)
    expect(screen.queryByText(/p\.\d/)).not.toBeInTheDocument()
  })
})

describe('SourceCard — types (icônes)', () => {
  it.each([
    ['pdf', '📄'],
    ['csv', '📊'],
    ['markdown', '📝'],
    ['url', '🌐'],
    ['txt', '📋'],
  ])('type %s → icône %s', (type, icon) => {
    render(<SourceCard source={makeSource({ type })} />)
    expect(screen.getByText(icon)).toBeInTheDocument()
  })

  it('type inconnu → icône défaut 📄', () => {
    render(<SourceCard source={makeSource({ type: 'docx' })} />)
    expect(screen.getByText('📄')).toBeInTheDocument()
  })
})
