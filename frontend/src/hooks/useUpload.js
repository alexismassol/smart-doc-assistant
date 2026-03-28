import { useState, useCallback, useEffect } from 'react'

/**
 * useUpload — Gestion de l'upload de fichiers et ingestion d'URLs
 * Uses: fetch API → POST /api/upload, POST /api/ingest-url, GET/DELETE /api/documents
 */
export function useUpload() {
  const [documents, setDocuments] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [health, setHealth] = useState(null)

  // Chargement initial des documents et de l'état du serveur
  useEffect(() => {
    fetchDocuments()
    fetchHealth()
  }, [])

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health')
      if (res.ok) setHealth(await res.json())
    } catch { /* silencieux */ }
  }

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents')
      if (res.ok) {
        const data = await res.json()
        setDocuments(data.documents || [])
      }
    } catch { /* silencieux */ }
  }

  const uploadFile = useCallback(async (file) => {
    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Erreur upload')
      await fetchDocuments()
      await fetchHealth()
      return { success: true, chunks: data.chunks_created }
    } catch (err) {
      return { success: false, error: err.message }
    } finally {
      setIsUploading(false)
    }
  }, [])

  const ingestUrl = useCallback(async (url) => {
    setIsUploading(true)
    try {
      const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Erreur ingestion URL')
      await fetchDocuments()
      await fetchHealth()
      return { success: true, chunks: data.chunks_created }
    } catch (err) {
      return { success: false, error: err.message }
    } finally {
      setIsUploading(false)
    }
  }, [])

  const deleteDoc = useCallback(async (source) => {
    try {
      const res = await fetch(`/api/documents/${encodeURIComponent(source)}`, { method: 'DELETE' })
      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.source !== source))
        await fetchHealth()
      }
    } catch { /* silencieux */ }
  }, [])

  return { documents, isUploading, uploadFile, ingestUrl, deleteDoc, health, refetch: fetchDocuments }
}
