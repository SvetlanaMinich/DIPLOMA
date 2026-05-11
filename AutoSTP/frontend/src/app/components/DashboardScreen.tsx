import { Search, Plus, Trash2, X, Upload } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { listDocuments, uploadDocument, deleteDocument } from '../../api/documents'
import { useDebounce } from '../../hooks/useDebounce'
import type { DocumentType } from '../../types/document'

const STATUS_COLORS: Record<string, string> = {
  uploaded: '#6B7280', inpr: '#D97706', formatted: '#16A34A',
}
const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded', inpr: 'Segmented', formatted: 'Formatted',
}
const TYPE_LABELS: Record<string, string> = { ku: 'CW', di: 'DT' }
const TYPE_COLORS: Record<string, string> = { ku: '#D97706', di: '#2563EB' }

export function DashboardScreen() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadType, setUploadType] = useState<DocumentType>('ku')
  const fileRef = useRef<HTMLInputElement>(null)
  const debouncedSearch = useDebounce(search, 300)

  useEffect(() => { document.title = 'My Documents — AutoSTP' }, [])

  const { data, isLoading } = useQuery({
    queryKey: ['documents', debouncedSearch],
    queryFn: () => listDocuments({ title_contains: debouncedSearch || undefined, limit: 50 }),
  })

  const uploadMut = useMutation({
    mutationFn: () => uploadDocument(uploadFile!, uploadTitle || undefined, uploadType),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ['documents'] })
      toast.success('Document uploaded')
      setShowUpload(false)
      setUploadFile(null)
      setUploadTitle('')
      navigate(`/documents/${doc.id}`)
    },
    onError: (e: unknown) => {
      const status = (e as { response?: { status: number } }).response?.status
      toast.error(status === 400 ? 'Unsupported file format (.docx and .txt only)' : status === 413 ? 'File too large (max 30 MB)' : 'Upload failed')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document deleted') },
    onError: () => toast.error('Failed to delete document'),
  })

  const docs = data?.items ?? []

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="flex items-center justify-between mb-6">
            <h1 style={{ color: '#111827' }}>My Documents</h1>
            <button onClick={() => setShowUpload(true)} className="flex items-center gap-2 px-4 py-2 text-white rounded-md" style={{ backgroundColor: '#2563EB', borderRadius: '6px', height: '44px' }}>
              <Plus size={20} /> Upload Document
            </button>
          </div>

          <div className="flex items-center justify-between mb-6">
            <div className="relative" style={{ width: '400px' }}>
              <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#6B7280' }} />
              <input
                type="text"
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
            </div>
            <span className="text-sm" style={{ color: '#6B7280' }}>
              Total: {data?.total ?? 0} documents
            </span>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-lg shadow-md h-48 animate-pulse" style={{ borderRadius: '8px' }} />
              ))}
            </div>
          ) : docs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24">
              <div className="mb-4" style={{ color: '#6B7280', fontSize: '64px' }}>📄</div>
              <p className="mb-4" style={{ color: '#6B7280' }}>
                {search ? 'No documents found' : 'Upload your first document'}
              </p>
              {!search && (
                <button onClick={() => setShowUpload(true)} className="px-6 py-2 text-white rounded-md" style={{ backgroundColor: '#2563EB', borderRadius: '6px' }}>
                  Upload Document
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-6">
              {docs.map((doc) => {
                const sc = STATUS_COLORS[doc.status] ?? '#6B7280'
                const tc = TYPE_COLORS[doc.document_type] ?? '#6B7280'
                return (
                  <div
                    key={doc.id}
                    className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
                    style={{ borderRadius: '8px' }}
                    onClick={() => navigate(`/documents/${doc.id}`)}
                  >
                    <div style={{ height: '4px', backgroundColor: '#2563EB' }} />
                    <div className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <span className="px-2 py-1 rounded text-xs text-white" style={{ backgroundColor: tc, borderRadius: '4px' }}>
                          {TYPE_LABELS[doc.document_type] ?? doc.document_type.toUpperCase()}
                        </span>
                      </div>
                      <h3 className="mb-3 line-clamp-2" style={{ color: '#111827' }}>{doc.title}</h3>
                      <div className="flex items-center gap-2 mb-3">
                        <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: sc + '20', color: sc, borderRadius: '4px' }}>
                          {STATUS_LABELS[doc.status] ?? doc.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm" style={{ color: '#6B7280' }}>
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            className="text-sm hover:underline"
                            style={{ color: '#2563EB' }}
                            onClick={(e) => { e.stopPropagation(); navigate(`/documents/${doc.id}`) }}
                          >
                            Open
                          </button>
                          <button
                            className="p-1 hover:bg-gray-100 rounded"
                            style={{ color: '#DC2626' }}
                            onClick={(e) => { e.stopPropagation(); setDeleteId(doc.id) }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md" style={{ borderRadius: '8px' }}>
            <div className="flex items-center justify-between mb-6">
              <h3 style={{ color: '#111827' }}>Upload Document</h3>
              <button onClick={() => { setShowUpload(false); setUploadFile(null) }} style={{ color: '#6B7280' }}><X size={20} /></button>
            </div>

            <div
              className="border-2 border-dashed rounded-lg p-8 mb-4 cursor-pointer hover:border-blue-400 transition-colors text-center"
              style={{ borderColor: uploadFile ? '#2563EB' : '#E5E7EB', borderRadius: '8px' }}
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={32} className="mx-auto mb-2" style={{ color: '#6B7280' }} />
              {uploadFile ? (
                <p style={{ color: '#111827' }}>{uploadFile.name}</p>
              ) : (
                <>
                  <p style={{ color: '#111827' }}>Click to select file</p>
                  <p className="text-sm mt-1" style={{ color: '#6B7280' }}>DOCX, TXT · Max 30 MB</p>
                </>
              )}
              <input ref={fileRef} type="file" accept=".docx,.txt" className="hidden" onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
            </div>

            <div className="mb-4">
              <label className="block mb-2" style={{ color: '#111827' }}>Title (optional)</label>
              <input
                type="text"
                placeholder="From filename if empty"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
            </div>

            <div className="mb-6">
              <label className="block mb-2" style={{ color: '#111827' }}>Document Type</label>
              <select
                value={uploadType}
                onChange={(e) => setUploadType(e.target.value as DocumentType)}
                className="w-full px-3 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              >
                <option value="ku">Coursework (CW)</option>
                <option value="di">Diploma thesis (DT)</option>
              </select>
            </div>

            <div className="flex gap-3">
              <button onClick={() => { setShowUpload(false); setUploadFile(null) }} className="flex-1 border rounded-md" style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', height: '44px' }}>
                Cancel
              </button>
              <button
                disabled={!uploadFile || uploadMut.isPending}
                onClick={() => uploadMut.mutate()}
                className="flex-1 text-white rounded-md"
                style={{ backgroundColor: !uploadFile || uploadMut.isPending ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: !uploadFile || uploadMut.isPending ? 'not-allowed' : 'pointer' }}
              >
                {uploadMut.isPending ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteId && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm" style={{ borderRadius: '8px' }}>
            <h3 className="mb-2" style={{ color: '#111827' }}>Delete document?</h3>
            <p className="mb-6" style={{ color: '#6B7280' }}>This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="flex-1 border rounded-md" style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', height: '44px' }}>
                Cancel
              </button>
              <button
                disabled={deleteMut.isPending}
                onClick={() => deleteMut.mutate(deleteId, { onSuccess: () => setDeleteId(null) })}
                className="flex-1 text-white rounded-md"
                style={{ backgroundColor: '#DC2626', borderRadius: '6px', height: '44px' }}
              >
                {deleteMut.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
