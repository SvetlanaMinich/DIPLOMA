import { ChevronLeft, Download, CheckCircle, AlertCircle } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { getDocument, formatDocument, exportDocx, exportPdf } from '../../api/documents'
import { listTemplates } from '../../api/templates'

const STATUS_COLORS: Record<string, string> = { uploaded: '#6B7280', inpr: '#D97706', formatted: '#16A34A' }
const STATUS_LABELS: Record<string, string> = { uploaded: 'Uploaded', inpr: 'Segmented', formatted: 'Formatted' }
const TYPE_COLORS: Record<string, string> = { ku: '#D97706', di: '#2563EB' }
const TYPE_LABELS: Record<string, string> = { ku: 'CW', di: 'DT' }

export function DocumentFormattingScreen() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [selectedTemplate, setSelectedTemplate] = useState('')

  const { data: doc, isLoading: docLoading, isError } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id!),
    enabled: !!id,
    retry: 1,
  })

  const { data: templatesData } = useQuery({
    queryKey: ['templates'],
    queryFn: () => listTemplates({ limit: 100 }),
  })
  const templates = templatesData?.items ?? []

  const formatMut = useMutation({
    mutationFn: () => formatDocument(id!, selectedTemplate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['document', id] })
      toast.success('Document formatted successfully')
    },
    onError: () => toast.error('Formatting failed'),
  })

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

  const sc = STATUS_COLORS[doc?.status ?? ''] ?? '#6B7280'
  const tc = TYPE_COLORS[doc?.document_type ?? ''] ?? '#6B7280'
  const isFormatted = doc?.status === 'formatted'

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
                {docLoading ? (
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
            <button onClick={() => navigate(`/documents/${id}`)} className="py-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Content</button>
            <button onClick={() => navigate(`/documents/${id}/sections`)} className="py-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Sections</button>
            <button className="py-4 border-b-2" style={{ borderColor: '#2563EB', color: '#2563EB' }}>Formatting</button>
          </div>
        </div>

        <div className="p-8">
          <div className="bg-white rounded-lg shadow-md p-6 max-w-2xl" style={{ borderRadius: '8px' }}>
            {isFormatted ? (
              <>
                <div className="flex items-center gap-3 p-4 rounded-lg mb-6" style={{ backgroundColor: '#16A34A10', border: '1px solid #16A34A' }}>
                  <CheckCircle size={20} style={{ color: '#16A34A' }} />
                  <span style={{ color: '#16A34A' }}>Document successfully formatted ✓</span>
                </div>
                <div className="flex gap-3 mb-6">
                  <button
                    onClick={() => doc && exportDocx(doc.id, `${doc.title}.docx`)}
                    className="flex-1 text-white rounded-md flex items-center justify-center gap-2"
                    style={{ backgroundColor: '#2563EB', borderRadius: '6px', height: '44px' }}
                  >
                    <Download size={18} /> Download DOCX
                  </button>
                  <button
                    onClick={() => doc && exportPdf(doc.id, `${doc.title}.pdf`)}
                    className="flex-1 border rounded-md flex items-center justify-center gap-2"
                    style={{ borderColor: '#2563EB', color: '#2563EB', borderRadius: '6px', height: '44px' }}
                  >
                    <Download size={18} /> Download PDF
                  </button>
                </div>
                <p className="text-sm text-center" style={{ color: '#6B7280' }}>
                  Formatted · {new Date(doc?.updated_at ?? '').toLocaleDateString()}
                </p>
              </>
            ) : (
              <>
                <div className="mb-6">
                  <label className="block mb-2" style={{ color: '#111827' }}>Template</label>
                  <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                    style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
                  >
                    <option value="">Select template...</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
                <button
                  disabled={!selectedTemplate || formatMut.isPending}
                  onClick={() => formatMut.mutate()}
                  className="w-full text-white rounded-md flex items-center justify-center gap-2"
                  style={{ backgroundColor: !selectedTemplate || formatMut.isPending ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: !selectedTemplate || formatMut.isPending ? 'not-allowed' : 'pointer' }}
                >
                  {formatMut.isPending ? 'Formatting...' : <><span>▶</span> Format Document</>}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
