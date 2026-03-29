/**
 * StatusBar.test.jsx - Tests unitaires du composant StatusBar
 * Uses: Vitest, React Testing Library
 *
 * Matrice de conformité :
 * - Nominal : llmProvider connu → label correct
 * - Bornes : llmProvider undefined → "Connexion...", documentsCount 0/1/N, latency null
 * - Contrats : pluriel/singulier pour documents, latence masquée si null
 * - Métadonnées : logo "Smart Doc Assistant" toujours présent
 */
import { render, screen } from '@testing-library/react'
import StatusBar from '../components/StatusBar.jsx'

describe('StatusBar - logo', () => {
  it('affiche le nom de l\'app', () => {
    render(<StatusBar documentsCount={0} />)
    expect(screen.getByText('Smart Doc Assistant')).toBeInTheDocument()
  })
})

describe('StatusBar - provider LLM', () => {
  it('ollama → label "Ollama local"', () => {
    render(<StatusBar llmProvider="ollama" documentsCount={0} />)
    expect(screen.getByText(/Ollama local/)).toBeInTheDocument()
  })

  it('mistral → label "Mistral API"', () => {
    render(<StatusBar llmProvider="mistral" documentsCount={0} />)
    expect(screen.getByText(/Mistral API/)).toBeInTheDocument()
  })

  it('anthropic → label "Claude"', () => {
    render(<StatusBar llmProvider="anthropic" documentsCount={0} />)
    expect(screen.getByText(/Claude/)).toBeInTheDocument()
  })

  it('provider undefined → label "Connexion..."', () => {
    render(<StatusBar documentsCount={0} />)
    expect(screen.getByText(/Connexion/)).toBeInTheDocument()
  })
})

describe('StatusBar - compteur documents', () => {
  it('0 documents → "0 documents"', () => {
    render(<StatusBar documentsCount={0} />)
    expect(screen.getByText(/0 documents/)).toBeInTheDocument()
  })

  it('1 document → singulier "1 document"', () => {
    render(<StatusBar documentsCount={1} />)
    expect(screen.getByText(/1 document$/)).toBeInTheDocument()
  })

  it('5 documents → pluriel "5 documents"', () => {
    render(<StatusBar documentsCount={5} />)
    expect(screen.getByText(/5 documents/)).toBeInTheDocument()
  })

  it('documentsCount undefined → 0 documents (défaut)', () => {
    render(<StatusBar />)
    expect(screen.getByText(/0 documents/)).toBeInTheDocument()
  })
})

describe('StatusBar - latence', () => {
  it('latency null → pas d\'affichage latence', () => {
    render(<StatusBar documentsCount={0} latency={null} />)
    expect(screen.queryByText(/ms/)).not.toBeInTheDocument()
  })

  it('latency 1240 → "1240 ms" affiché', () => {
    render(<StatusBar documentsCount={0} latency={1240} />)
    expect(screen.getByText(/1240 ms/)).toBeInTheDocument()
  })

  it('latency 0 → "0 ms" affiché (borne basse)', () => {
    render(<StatusBar documentsCount={0} latency={0} />)
    // latency=0 est falsy, donc non affiché selon l'impl (latency != null mais 0 est falsy)
    // Le composant utilise latency != null, donc 0 devrait s'afficher
    // En réalité latency={0} est != null donc affiché
    expect(screen.getByText(/0 ms/)).toBeInTheDocument()
  })
})
