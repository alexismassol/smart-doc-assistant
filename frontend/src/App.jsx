import StatusBar from './components/StatusBar.jsx'
import UploadPanel from './components/UploadPanel.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import { useChat } from './hooks/useChat.js'
import { useUpload } from './hooks/useUpload.js'

export default function App() {
  const chat = useChat()
  const upload = useUpload()

  return (
    <div className="flex flex-col overflow-hidden" style={{ height: '100dvh' }}>
      {/* Barre de statut en haut */}
      <StatusBar
        llmProvider={upload.health?.llm_provider}
        documentsCount={upload.health?.documents_count ?? 0}
        latency={chat.lastLatency}
      />

      {/* Layout principal : upload gauche (desktop), chat droite — stack vertical sur mobile */}
      <div className="flex flex-1 overflow-hidden flex-col md:flex-row min-h-0">
        <UploadPanel
          documents={upload.documents}
          isUploading={upload.isUploading}
          onUploadFile={upload.uploadFile}
          onIngestUrl={upload.ingestUrl}
          onDeleteDoc={upload.deleteDoc}
          onLoadSession={chat.loadSession}
          activeSessionId={chat.sessionId}
        />
        <ChatWindow
          messages={chat.messages}
          isLoading={chat.isLoading}
          onSend={chat.sendMessage}
          onReset={chat.reset}
        />
      </div>
    </div>
  )
}
