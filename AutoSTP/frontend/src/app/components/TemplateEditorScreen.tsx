import { Save, Trash2, X } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { getTemplate, updateTemplate, deleteTemplate } from '../../api/templates'

export function TemplateEditorScreen() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const [viewMode, setViewMode] = useState<'preview' | 'json'>('preview')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [jsonText, setJsonText] = useState('')
  const [jsonError, setJsonError] = useState('')
  const [showDelete, setShowDelete] = useState(false)
  const [editingName, setEditingName] = useState(false)

  const { data: template, isLoading } = useQuery({
    queryKey: ['template', id],
    queryFn: () => getTemplate(id!),
    enabled: !!id,
  })

  useEffect(() => {
    if (template) {
      setName(template.name)
      setDescription(template.description ?? '')
      setJsonText(JSON.stringify(template.template_json, null, 2))
    }
  }, [template?.id])

  const saveMut = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown>
      try { parsed = JSON.parse(jsonText) } catch { throw new Error('Invalid JSON') }
      return updateTemplate(id!, { name, description, template_json: parsed })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['template', id] })
      qc.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template saved')
      setJsonError('')
    },
    onError: (e: unknown) => {
      const msg = (e as Error).message
      if (msg === 'Invalid JSON') { setJsonError('Invalid JSON syntax'); toast.error('Invalid JSON') }
      else toast.error('Failed to save template')
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteTemplate(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template deleted')
      navigate('/templates')
    },
    onError: () => toast.error('Failed to delete template'),
  })

  const isSystem = template?.type === 'system'

  const previewSections = template ? Object.entries(template.template_json).map(([key, val]) => ({
    title: key,
    value: typeof val === 'object' ? JSON.stringify(val) : String(val),
  })) : []

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          {isLoading ? (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6 animate-pulse" style={{ borderRadius: '8px', height: '80px' }} />
          ) : (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6" style={{ borderRadius: '8px' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3 flex-1">
                  {editingName && !isSystem ? (
                    <input
                      autoFocus
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      onBlur={() => setEditingName(false)}
                      className="px-3 py-1 border rounded-md"
                      style={{ borderColor: '#E5E7EB', borderRadius: '6px', fontSize: '20px', fontWeight: 600, color: '#111827' }}
                    />
                  ) : (
                    <h2
                      style={{ color: '#111827', cursor: isSystem ? 'default' : 'pointer' }}
                      onClick={() => !isSystem && setEditingName(true)}
                    >
                      {name}
                    </h2>
                  )}
                  {isSystem && (
                    <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#2563EB20', color: '#2563EB', borderRadius: '4px' }}>system</span>
                  )}
                </div>
                {!isSystem && (
                  <div className="flex items-center gap-3">
                    <button
                      disabled={saveMut.isPending}
                      onClick={() => saveMut.mutate()}
                      className="px-6 py-2 text-white rounded-md flex items-center gap-2"
                      style={{ backgroundColor: saveMut.isPending ? '#93C5FD' : '#2563EB', borderRadius: '6px' }}
                    >
                      <Save size={18} /> {saveMut.isPending ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setShowDelete(true)}
                      className="px-6 py-2 border rounded-md flex items-center gap-2"
                      style={{ borderColor: '#DC2626', color: '#DC2626', borderRadius: '6px' }}
                    >
                      <Trash2 size={18} /> Delete
                    </button>
                  </div>
                )}
              </div>

              {!isSystem && (
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Description (optional)"
                  className="w-full px-3 py-2 border rounded-md mb-4"
                  style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '40px', color: '#6B7280' }}
                />
              )}

              <div className="inline-flex rounded-md p-1" style={{ backgroundColor: '#F8FAFC' }}>
                <button
                  onClick={() => setViewMode('preview')}
                  className="px-4 py-2 rounded-md transition-colors"
                  style={{ backgroundColor: viewMode === 'preview' ? '#FFFFFF' : 'transparent', color: viewMode === 'preview' ? '#2563EB' : '#6B7280', borderRadius: '6px' }}
                >
                  Preview
                </button>
                <button
                  onClick={() => setViewMode('json')}
                  className="px-4 py-2 rounded-md transition-colors"
                  style={{ backgroundColor: viewMode === 'json' ? '#FFFFFF' : 'transparent', color: viewMode === 'json' ? '#2563EB' : '#6B7280', borderRadius: '6px' }}
                >
                  JSON
                </button>
              </div>
            </div>
          )}

          {viewMode === 'preview' ? (
            <div className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
              {previewSections.length === 0 ? (
                <p style={{ color: '#6B7280' }}>No parameters defined yet.</p>
              ) : (
                <table className="w-full">
                  <tbody>
                    {previewSections.map((row, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: '#E5E7EB' }}>
                        <td className="py-3 pr-8 w-1/3" style={{ color: '#6B7280' }}>{row.title}</td>
                        <td className="py-3" style={{ color: '#111827', wordBreak: 'break-all' }}>{row.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
              {jsonError && <p className="text-sm mb-2" style={{ color: '#DC2626' }}>{jsonError}</p>}
              <textarea
                readOnly={isSystem}
                value={jsonText}
                onChange={(e) => { setJsonText(e.target.value); setJsonError('') }}
                className="w-full outline-none resize-none"
                style={{ minHeight: '500px', color: '#111827', fontFamily: 'monospace', fontSize: '13px', borderColor: jsonError ? '#DC2626' : 'transparent' }}
              />
            </div>
          )}
        </div>
      </div>

      {showDelete && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm" style={{ borderRadius: '8px' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 style={{ color: '#111827' }}>Delete template?</h3>
              <button onClick={() => setShowDelete(false)} style={{ color: '#6B7280' }}><X size={20} /></button>
            </div>
            <p className="mb-6" style={{ color: '#6B7280' }}>This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setShowDelete(false)} className="flex-1 border rounded-md" style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', height: '44px' }}>
                Cancel
              </button>
              <button
                disabled={deleteMut.isPending}
                onClick={() => deleteMut.mutate()}
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
