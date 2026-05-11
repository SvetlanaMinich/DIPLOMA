import { ChevronLeft, Download, ChevronDown, AlertCircle } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { getDocument, segmentDocument, getHints, exportDocx, exportPdf } from '../../api/documents'
import { listTemplates } from '../../api/templates'
import type { SectionOut } from '../../types/document'

const STATUS_COLORS: Record<string, string> = { uploaded: '#6B7280', inpr: '#D97706', formatted: '#16A34A' }
const STATUS_LABELS: Record<string, string> = { uploaded: 'Uploaded', inpr: 'Segmented', formatted: 'Formatted' }
const TYPE_COLORS: Record<string, string> = { ku: '#D97706', di: '#2563EB' }
const TYPE_LABELS: Record<string, string> = { ku: 'CW', di: 'DT' }

const ROLE_COLORS: Record<string, string> = {
  introduction: '#2563EB', theory: '#16A34A', practical: '#D97706', conclusion: '#6B7280',
  bibliography: '#9333EA', appendix: '#0891B2',
}

export function DocumentSectionsScreen() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [sections, setSections] = useState<SectionOut[]>([])
  const [unmatched, setUnmatched] = useState(0)
  const [segmented, setSegmented] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [hints, setHints] = useState<Record<string, string[]>>({})

  const { data: doc, isLoading: docLoading, isError } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocument(id!),
    enabled: !!id,
    retry: 1,
  })

  useEffect(() => {
    if (doc && (doc.status === 'inpr' || doc.status === 'formatted')) {
      setSegmented(true)
    }
  }, [doc?.status])

  const { data: templatesData } = useQuery({
    queryKey: ['templates'],
    queryFn: () => listTemplates({ limit: 100 }),
  })
  const templates = templatesData?.items ?? []

  const segmentMut = useMutation({
    mutationFn: () => segmentDocument(id!, selectedTemplate),
    onSuccess: (res) => {
      setSections(res.sections)
      setUnmatched(res.unmatched_chars)
      setSegmented(true)
      qc.invalidateQueries({ queryKey: ['document', id] })
      toast.success(`Found ${res.total_sections} sections`)
    },
    onError: () => toast.error('Segmentation failed'),
  })

  const hintsMut = useMutation({
    mutationFn: (sectionId: string) => getHints(id!, sectionId),
    onSuccess: (res) => {
      setHints((prev) => ({ ...prev, [res.section_id]: res.hints }))
    },
    onError: () => toast.error('Failed to get hints'),
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
            <button className="py-4 border-b-2" style={{ borderColor: '#2563EB', color: '#2563EB' }}>Sections</button>
            <button onClick={() => navigate(`/documents/${id}/formatting`)} className="py-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Formatting</button>
          </div>
        </div>

        <div className="p-8">
          {!segmented ? (
            <div className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
              <div className="flex items-start gap-3 p-4 rounded-lg mb-6" style={{ backgroundColor: '#D9770610', borderLeft: '4px solid #D97706' }}>
                <AlertCircle size={20} style={{ color: '#D97706', marginTop: '2px' }} />
                <span style={{ color: '#D97706' }}>Document is not segmented. Select a template and start analysis.</span>
              </div>
              <div className="mb-4">
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
                disabled={!selectedTemplate || segmentMut.isPending}
                onClick={() => segmentMut.mutate()}
                className="w-full text-white rounded-md flex items-center justify-center gap-2"
                style={{ backgroundColor: !selectedTemplate || segmentMut.isPending ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: !selectedTemplate || segmentMut.isPending ? 'not-allowed' : 'pointer' }}
              >
                {segmentMut.isPending ? (
                  <>
                    <span className="animate-spin">⚡</span> Segmenting...
                  </>
                ) : (
                  <><span>⚡</span> Segment</>
                )}
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between p-4 rounded-lg mb-6" style={{ backgroundColor: '#16A34A10', border: '1px solid #16A34A' }}>
                <span style={{ color: '#16A34A' }}>Found {sections.length} sections · Unmatched: {unmatched} chars</span>
                <button
                  onClick={() => setSegmented(false)}
                  className="px-4 py-2 border rounded-md"
                  style={{ borderColor: '#E5E7EB', color: '#111827', borderRadius: '6px' }}
                >
                  Re-segment
                </button>
              </div>

              <div className="space-y-4">
                {sections.map((section) => {
                  const roleColor = ROLE_COLORS[section.role] ?? '#6B7280'
                  const isExpanded = expandedId === section.id
                  const sectionHints = hints[section.id]
                  return (
                    <div key={section.id} className="bg-white rounded-lg shadow-md overflow-hidden" style={{ borderRadius: '8px' }}>
                      <div className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="px-2 py-1 rounded text-xs text-white" style={{ backgroundColor: roleColor, borderRadius: '4px' }}>{section.role}</span>
                            <h3 style={{ color: '#111827' }}>{section.title}</h3>
                          </div>
                          <button onClick={() => setExpandedId(isExpanded ? null : section.id)}>
                            <ChevronDown size={20} style={{ color: '#6B7280', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
                          </button>
                        </div>
                        <p className="text-sm mb-3" style={{ color: '#6B7280' }}>Characters: {section.char_count} · Level: {section.level}</p>
                        {isExpanded && (
                          <>
                            {section.text_preview && (
                              <p className="italic mb-4 text-sm" style={{ color: '#6B7280' }}>{section.text_preview}</p>
                            )}
                            <button
                              disabled={hintsMut.isPending && hintsMut.variables === section.id}
                              onClick={() => !sectionHints && hintsMut.mutate(section.id)}
                              className="text-sm mb-3"
                              style={{ color: '#2563EB' }}
                            >
                              {hintsMut.isPending && hintsMut.variables === section.id ? 'Loading hints...' : sectionHints ? 'Hints ▼' : 'Get Hints ▼'}
                            </button>
                            {sectionHints && sectionHints.length > 0 && (
                              <div className="p-4 rounded-lg" style={{ backgroundColor: '#2563EB10' }}>
                                <ul className="space-y-2">
                                  {sectionHints.map((hint, i) => (
                                    <li key={i} className="text-sm flex gap-2" style={{ color: '#111827' }}>
                                      <span style={{ color: '#2563EB' }}>•</span><span>{hint}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
