/**
 * UploadPanel.test.jsx - Tests Vitest + React Testing Library
 * Uses: Vitest, @testing-library/react, @testing-library/user-event
 * Couvre : drop zone, feedback success/error, URL form, document list, delete
 */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import UploadPanel from '../components/UploadPanel'

// ── Helpers ───────────────────────────────────────────────────────────────────

const defaultProps = {
  documents: [],
  isUploading: false,
  onUploadFile: vi.fn(),
  onIngestUrl: vi.fn(),
  onDeleteDoc: vi.fn(),
}

function renderPanel(props = {}) {
  return render(<UploadPanel {...defaultProps} {...props} />)
}

// ── Drop zone rendering ────────────────────────────────────────────────────────

describe('UploadPanel - drop zone', () => {
  it('affiche le texte "Déposer un fichier" par défaut', () => {
    renderPanel()
    expect(screen.getByText('Déposer un fichier')).toBeInTheDocument()
  })

  it('affiche les formats acceptés (PDF · CSV · MD · TXT)', () => {
    renderPanel()
    expect(screen.getByText('PDF · CSV · MD · TXT')).toBeInTheDocument()
  })

  it('affiche le spinner "Indexation..." quand isUploading=true', () => {
    renderPanel({ isUploading: true })
    expect(screen.getByText('Indexation...')).toBeInTheDocument()
  })

  it('masque le texte "Déposer un fichier" quand isUploading=true', () => {
    renderPanel({ isUploading: true })
    expect(screen.queryByText('Déposer un fichier')).not.toBeInTheDocument()
  })

  it('contient un input file caché avec accept=".pdf,.csv,.md,.txt"', () => {
    renderPanel()
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeTruthy()
    expect(input.accept).toBe('.pdf,.csv,.md,.txt')
  })
})

// ── Feedback toast ─────────────────────────────────────────────────────────────

describe('UploadPanel - feedback upload', () => {
  it('affiche le feedback success après un upload réussi', async () => {
    const onUploadFile = vi.fn().mockResolvedValue({ success: true, chunks: 5 })
    renderPanel({ onUploadFile })

    const input = document.querySelector('input[type="file"]')
    const file = new File(['contenu'], 'doc.pdf', { type: 'application/pdf' })
    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } })
    })

    await waitFor(() => {
      expect(screen.getByText(/doc\.pdf - 5 chunks indexés/)).toBeInTheDocument()
    })
  })

  it('affiche le feedback error après un upload échoué', async () => {
    const onUploadFile = vi.fn().mockResolvedValue({ success: false, error: 'Format non supporté' })
    renderPanel({ onUploadFile })

    const input = document.querySelector('input[type="file"]')
    const file = new File(['x'], 'bad.exe', { type: 'application/octet-stream' })
    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } })
    })

    await waitFor(() => {
      expect(screen.getByText('Format non supporté')).toBeInTheDocument()
    })
  })

  it('le feedback disparaît après 3 secondes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const onUploadFile = vi.fn().mockResolvedValue({ success: true, chunks: 3 })
    renderPanel({ onUploadFile })

    const input = document.querySelector('input[type="file"]')
    const file = new File(['x'], 'test.md', { type: 'text/markdown' })
    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } })
    })

    await waitFor(() => {
      expect(screen.getByText(/test\.md - 3 chunks indexés/)).toBeInTheDocument()
    })

    act(() => { vi.advanceTimersByTime(3001) })

    await waitFor(() => {
      expect(screen.queryByText(/test\.md/)).not.toBeInTheDocument()
    })

    vi.useRealTimers()
  })
})

// ── URL form ───────────────────────────────────────────────────────────────────

describe('UploadPanel - formulaire URL', () => {
  it('rend un input de type url avec placeholder "https://..."', () => {
    renderPanel()
    const input = screen.getByPlaceholderText('https://...')
    expect(input).toBeInTheDocument()
    expect(input.type).toBe('url')
  })

  it('le bouton "+" est désactivé si le champ URL est vide', () => {
    renderPanel()
    const btn = screen.getByRole('button', { name: '+' })
    expect(btn).toBeDisabled()
  })

  it('le bouton "+" est activé quand une URL est saisie', async () => {
    renderPanel()
    const input = screen.getByPlaceholderText('https://...')
    await userEvent.type(input, 'https://example.com')
    const btn = screen.getByRole('button', { name: '+' })
    expect(btn).not.toBeDisabled()
  })

  it('le bouton "+" est désactivé quand isUploading=true', async () => {
    renderPanel({ isUploading: true })
    const input = screen.getByPlaceholderText('https://...')
    await userEvent.type(input, 'https://example.com')
    const btn = screen.getByRole('button', { name: '+' })
    expect(btn).toBeDisabled()
  })

  it('appelle onIngestUrl avec l\'URL saisie lors de la soumission', async () => {
    const onIngestUrl = vi.fn().mockResolvedValue({ success: true, chunks: 2 })
    renderPanel({ onIngestUrl })
    const input = screen.getByPlaceholderText('https://...')
    await userEvent.type(input, 'https://example.com/doc')
    await userEvent.click(screen.getByRole('button', { name: '+' }))
    expect(onIngestUrl).toHaveBeenCalledWith('https://example.com/doc')
  })

  it('vide le champ URL après une soumission réussie', async () => {
    const onIngestUrl = vi.fn().mockResolvedValue({ success: true, chunks: 1 })
    renderPanel({ onIngestUrl })
    const input = screen.getByPlaceholderText('https://...')
    await userEvent.type(input, 'https://example.com')
    await userEvent.click(screen.getByRole('button', { name: '+' }))
    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('ne soumet pas si l\'URL est uniquement des espaces', async () => {
    const onIngestUrl = vi.fn()
    renderPanel({ onIngestUrl })
    const input = screen.getByPlaceholderText('https://...')
    await userEvent.type(input, '   ')
    fireEvent.submit(input.closest('form'))
    expect(onIngestUrl).not.toHaveBeenCalled()
  })
})

// ── Liste de documents ─────────────────────────────────────────────────────────

describe('UploadPanel - liste des documents', () => {
  it('affiche "Aucun document indexé" quand la liste est vide', () => {
    renderPanel({ documents: [] })
    expect(screen.getByText('Aucun document indexé')).toBeInTheDocument()
  })

  it('affiche le nom du document', () => {
    const docs = [{ source: 'rapport.pdf', type: 'pdf', chunk_count: 10 }]
    renderPanel({ documents: docs })
    expect(screen.getByText('rapport.pdf')).toBeInTheDocument()
  })

  it('affiche le nombre de chunks', () => {
    const docs = [{ source: 'data.csv', type: 'csv', chunk_count: 42 }]
    renderPanel({ documents: docs })
    expect(screen.getByText('42 chunks')).toBeInTheDocument()
  })

  it('affiche le type du document (3 premières lettres en majuscules)', () => {
    const docs = [{ source: 'doc.pdf', type: 'pdf', chunk_count: 5 }]
    renderPanel({ documents: docs })
    expect(screen.getByText('pdf')).toBeInTheDocument()
  })

  it('affiche plusieurs documents', () => {
    const docs = [
      { source: 'a.pdf', type: 'pdf', chunk_count: 3 },
      { source: 'b.csv', type: 'csv', chunk_count: 7 },
    ]
    renderPanel({ documents: docs })
    expect(screen.getByText('a.pdf')).toBeInTheDocument()
    expect(screen.getByText('b.csv')).toBeInTheDocument()
  })

  it('n\'affiche plus "Aucun document indexé" quand il y a des documents', () => {
    const docs = [{ source: 'doc.md', type: 'markdown', chunk_count: 2 }]
    renderPanel({ documents: docs })
    expect(screen.queryByText('Aucun document indexé')).not.toBeInTheDocument()
  })
})

// ── Suppression de document ────────────────────────────────────────────────────

describe('UploadPanel - suppression de document', () => {
  it('appelle onDeleteDoc avec le source du document au clic sur supprimer', async () => {
    const onDeleteDoc = vi.fn()
    const docs = [{ source: 'rapport.pdf', type: 'pdf', chunk_count: 10 }]
    renderPanel({ documents: docs, onDeleteDoc })

    // Le bouton de suppression est visible au hover - on le cherche par title
    const deleteBtn = screen.getByTitle('Supprimer')
    await userEvent.click(deleteBtn)

    expect(onDeleteDoc).toHaveBeenCalledWith('rapport.pdf')
  })

  it('affiche un bouton supprimer par document', () => {
    const docs = [
      { source: 'a.pdf', type: 'pdf', chunk_count: 1 },
      { source: 'b.csv', type: 'csv', chunk_count: 2 },
    ]
    renderPanel({ documents: docs })
    const deleteBtns = screen.getAllByTitle('Supprimer')
    expect(deleteBtns).toHaveLength(2)
  })
})

// ── Header ─────────────────────────────────────────────────────────────────────

describe('UploadPanel - header', () => {
  it('affiche le titre "Documents"', () => {
    renderPanel()
    expect(screen.getByText('Documents')).toBeInTheDocument()
  })
})
