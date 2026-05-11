import { ChevronLeft, Download, AlertCircle } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { getDocument, updateDocument, exportDocx, exportPdf } from '../../api/documents'

const STATUS_COLORS: Record<string, string> = { uploaded: '#6B7280', inpr: '#D97706', formatted: '#16A34A' }
const STATUS_LABELS: Record<string, string> = { uploaded: 'Uploaded', inpr: 'Segmented', formatted: 'Formatted' }
const TYPE_COLORS: Record<string, string> = { ku: '#D97706', di: '#2563EB' }
const TYPE_LABELS: Record<string, string> = { ku: 'CW', di: 'DT' }

export function DocumentContentScreen() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [text, setText] = useState('')
  const [saveState, setSaveState] = useState<'saved' | 'unsaved' | 'saving'>('saved')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id!),
    enabled: !!id,
    retry: 1,
  })

  useEffect(() => {
    if (doc?.current_version?.snapshot?.plain_text) {
      setText(doc.current_version.snapshot.plain_text)
    }
  }, [doc?.id])

  useEffect(() => {
    document.title = doc ? `${doc.title} — AutoSTP` : 'AutoSTP'
    return () => { document.title = 'AutoSTP' }
  }, [doc?.title])

  const saveMut = useMutation({
    mutationFn: (newText: string) =>
      updateDocument(id!, { snapshot: { plain_text: newText, nodes: doc?.current_version?.snapshot?.nodes ?? [] } }),
    onSuccess: () => { setSaveState('saved'); qc.invalidateQueries({ queryKey: ['document', id] }) },
    onError: () => { setSaveState('unsaved'); toast.error('Failed to save') },
  })

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    setText(val)
    setSaveState('unsaved')
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setSaveState('saving')
      saveMut.mutate(val)
    }, 2000)
  }

  const sc = STATUS_COLORS[doc?.status ?? ''] ?? '#6B7280'
  const tc = TYPE_COLORS[doc?.document_type ?? ''] ?? '#6B7280'
  const isFormatted = doc?.status === 'formatted'

  if (isError) {
    return (
      <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
        <Sidebar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <AlertCircle size={48} style={{ color: '#DC2626' }} />
          <p style={{ color: '#111827', fontSize: '18px' }}>Document not found</p>
          <button onClick={() => navigate('/')} className="px-6 py-2 text-white rounded-md" style={{ backgroundColor: '#2563EB', borderRadius: '6px' }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b" style={{ borderColor: '#E5E7EB' }}>
          <div className="px-8 py-4 border-b" style={{ borderColor: '#E5E7EB' }}>
            <button onClick={() => navigate('/')} className="flex items-center gap-2 mb-3 hover:underline" style={{ color: '#2563EB' }}>
              <ChevronLeft size={20} /> Back
            </button>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isLoading ? (
                  <div className="h-7 w-64 rounded animate-pulse" style={{ backgroundColor: '#E5E7EB' }} />
                ) : (
                  <h2 style={{ color: '#111827' }}>{doc?.title ?? 'Document'}</h2>
                )}
              </div>
              <div className="flex items-center gap-3">
                {doc && (
                  <>
                    <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: sc + '20', color: sc, borderRadius: '4px' }}>
                      {STATUS_LABELS[doc.status] ?? doc.status}
                    </span>
                    <span className="px-2 py-1 rounded text-xs text-white" style={{ backgroundColor: tc, borderRadius: '4px' }}>
                      {TYPE_LABELS[doc.document_type] ?? doc.document_type.toUpperCase()}
                    </span>
                  </>
                )}
                <button
                  disabled={!isFormatted}
                  onClick={() => doc && exportDocx(doc.id, `${doc.title}.docx`)}
                  className="flex items-center gap-2 px-4 py-2 border rounded-md"
                  style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', opacity: isFormatted ? 1 : 0.5, cursor: isFormatted ? 'pointer' : 'not-allowed' }}
                >
                  <Download size={18} /> DOCX
                </button>
                <button
                  disabled={!isFormatted}
                  onClick={() => doc && exportPdf(doc.id, `${doc.title}.pdf`)}
                  className="flex items-center gap-2 px-4 py-2 border rounded-md"
                  style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', opacity: isFormatted ? 1 : 0.5, cursor: isFormatted ? 'pointer' : 'not-allowed' }}
                >
                  <Download size={18} /> PDF
                </button>
              </div>
            </div>
          </div>

          <div className="flex gap-8 px-8">
            <button className="py-4 border-b-2" style={{ borderColor: '#2563EB', color: '#2563EB' }}>Content</button>
            <button onClick={() => navigate(`/documents/${id}/sections`)} className="py-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Sections</button>
            <button onClick={() => navigate(`/documents/${id}/formatting`)} className="py-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Formatting</button>
          </div>
        </div>

        <div className="p-8">
          <div className="bg-white rounded-lg shadow-md" style={{ borderRadius: '8px' }}>
            {isLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-4 rounded animate-pulse" style={{ backgroundColor: '#E5E7EB', width: i % 2 === 0 ? '90%' : '100%' }} />
                ))}
              </div>
            ) : (
              <>
                <textarea
                  value={text}
                  onChange={handleTextChange}
                  className="w-full p-6 outline-none resize-none"
                  style={{ minHeight: '500px', color: '#111827', fontFamily: 'inherit', fontSize: '14px', lineHeight: '1.7' }}
                  placeholder="Document content will appear here..."
                />
                <div className="px-6 py-3 border-t flex justify-end" style={{ borderColor: '#E5E7EB' }}>
                  <span className="text-sm flex items-center gap-2" style={{ color: '#6B7280' }}>
                    {saveState === 'saved' && 'Saved ✓'}
                    {saveState === 'unsaved' && 'Unsaved changes'}
                    {saveState === 'saving' && 'Saving...'}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
