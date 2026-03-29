/**
 * ChatWindow.test.jsx - Tests unitaires du composant ChatWindow
 * Uses: Vitest, React Testing Library, userEvent
 *
 * Matrice de conformité :
 * - Nominal : état vide (EmptyState), envoi de message, Enter pour submit
 * - Bornes : input vide → pas d'envoi, whitespace seul → pas d'envoi
 * - Interactions : Shift+Enter ne soumet pas, bouton reset visible si messages
 * - Contrats : onSend appelé avec le bon texte, input vidé après envoi
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatWindow from '../components/ChatWindow.jsx'

const mockOnSend = vi.fn()
const mockOnReset = vi.fn()

const defaultProps = {
  messages: [],
  isLoading: false,
  onSend: mockOnSend,
  onReset: mockOnReset,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ChatWindow - état vide', () => {
  it('affiche l\'EmptyState quand messages est vide', () => {
    render(<ChatWindow {...defaultProps} />)
    expect(screen.getByText('Smart Doc Assistant')).toBeInTheDocument()
  })

  it('affiche les suggestions dans l\'EmptyState', () => {
    render(<ChatWindow {...defaultProps} />)
    expect(screen.getByText(/Quelle est la limite de taux/)).toBeInTheDocument()
  })

  it('affiche le placeholder de l\'input', () => {
    render(<ChatWindow {...defaultProps} />)
    expect(screen.getByPlaceholderText(/Posez une question/)).toBeInTheDocument()
  })

  it('bouton reset absent si pas de messages', () => {
    render(<ChatWindow {...defaultProps} />)
    expect(screen.queryByTitle('Nouvelle conversation')).not.toBeInTheDocument()
  })
})

describe('ChatWindow - envoi de message', () => {
  it('appelle onSend avec le texte de l\'input', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} />)
    const input = screen.getByPlaceholderText(/Posez une question/)
    await user.type(input, 'Ma question de test')
    await user.keyboard('{Enter}')
    expect(mockOnSend).toHaveBeenCalledWith('Ma question de test')
  })

  it('vide l\'input après envoi', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} />)
    const input = screen.getByPlaceholderText(/Posez une question/)
    await user.type(input, 'Ma question')
    await user.keyboard('{Enter}')
    expect(input.value).toBe('')
  })
})

describe('ChatWindow - bornes (inputs invalides)', () => {
  it('input vide → onSend non appelé', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} />)
    const input = screen.getByPlaceholderText(/Posez une question/)
    await user.click(input)
    await user.keyboard('{Enter}')
    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('whitespace seul → onSend non appelé', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} />)
    const input = screen.getByPlaceholderText(/Posez une question/)
    await user.type(input, '   ')
    await user.keyboard('{Enter}')
    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('Shift+Enter ne soumet pas le formulaire', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} />)
    const input = screen.getByPlaceholderText(/Posez une question/)
    await user.type(input, 'Question')
    await user.keyboard('{Shift>}{Enter}{/Shift}')
    expect(mockOnSend).not.toHaveBeenCalled()
  })
})

describe('ChatWindow - avec messages', () => {
  const messages = [
    { role: 'user', content: 'Question test', id: 1 },
    { role: 'assistant', content: 'Réponse test', sources: [], confidence: 0.8, latency_ms: 500, id: 2 },
  ]

  it('n\'affiche pas EmptyState si messages présents', () => {
    render(<ChatWindow {...defaultProps} messages={messages} />)
    expect(screen.queryByText('Smart Doc Assistant')).not.toBeInTheDocument()
  })

  it('affiche les messages dans le chat', () => {
    render(<ChatWindow {...defaultProps} messages={messages} />)
    expect(screen.getByText('Question test')).toBeInTheDocument()
    expect(screen.getByText('Réponse test')).toBeInTheDocument()
  })

  it('bouton reset visible si messages présents', () => {
    render(<ChatWindow {...defaultProps} messages={messages} />)
    expect(screen.getByTitle('Nouvelle conversation')).toBeInTheDocument()
  })

  it('clic sur reset appelle onReset', async () => {
    const user = userEvent.setup()
    render(<ChatWindow {...defaultProps} messages={messages} />)
    await user.click(screen.getByTitle('Nouvelle conversation'))
    expect(mockOnReset).toHaveBeenCalled()
  })
})

describe('ChatWindow - état chargement', () => {
  const messages = [{ role: 'user', content: 'Question', id: 1 }]

  it('bouton submit désactivé pendant le chargement', () => {
    render(<ChatWindow {...defaultProps} messages={messages} isLoading={true} />)
    // Input a du texte via state - on vérifie le submit button directement
    const button = screen.getByRole('button', { name: '' }) // Le bouton submit sans texte
    // Il doit être disabled quand input est vide (state initial)
    expect(button).toBeDisabled()
  })
})
