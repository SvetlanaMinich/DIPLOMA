import { Plus, Zap, Lock, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { listTemplates, deleteTemplate, createTemplate } from '../../api/templates'

export function TemplatesListScreen() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => listTemplates({ limit: 100 }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); toast.success('Template deleted'); setDeleteId(null) },
    onError: () => toast.error('Failed to delete template'),
  })

  const createMut = useMutation({
    mutationFn: () => createTemplate({ name: newName, description: newDesc, template_json: {}, type: 'personal' }),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template created')
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      navigate(`/templates/${t.id}`)
    },
    onError: () => toast.error('Failed to create template'),
  })

  const all = data?.items ?? []
  const systemTemplates = all.filter((t) => t.type === 'system')
  const myTemplates = all.filter((t) => t.type === 'personal')

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="flex items-center justify-between mb-8">
            <h1 style={{ color: '#111827' }}>Formatting Templates</h1>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center gap-2 px-4 py-2 border rounded-md"
                style={{ borderColor: '#2563EB', color: '#2563EB', borderRadius: '6px', height: '44px' }}
              >
                <Plus size={20} /> Create Manually
              </button>
              <button
                onClick={() => navigate('/templates/extract')}
                className="flex items-center gap-2 px-4 py-2 text-white rounded-md"
                style={{ backgroundColor: '#2563EB', borderRadius: '6px', height: '44px' }}
              >
                <Zap size={20} /> Extract from Standard
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => <div key={i} className="bg-white rounded-lg shadow-md h-24 animate-pulse" style={{ borderRadius: '8px' }} />)}
            </div>
          ) : (
            <>
              {systemTemplates.length > 0 && (
                <div className="mb-8">
                  <h3 className="mb-4" style={{ color: '#6B7280' }}>System Templates</h3>
                  <div className="space-y-4">
                    {systemTemplates.map((t) => (
                      <div key={t.id} className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
                        <div className="flex items-start justify-between">
                          <div className="flex gap-4 flex-1">
                            <Lock size={24} style={{ color: '#6B7280' }} />
                            <div className="flex-1">
                              <h3 className="mb-2" style={{ color: '#111827' }}>{t.name}</h3>
                              {t.description && <p className="text-sm mb-2" style={{ color: '#6B7280' }}>{t.description}</p>}
                              <p className="text-sm" style={{ color: '#6B7280' }}>Updated: {new Date(t.updated_at).toLocaleDateString()}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => navigate(`/templates/${t.id}`)}
                            className="px-6 py-2 text-white rounded-md"
                            style={{ backgroundColor: '#2563EB', borderRadius: '6px' }}
                          >
                            Open
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="mb-4" style={{ color: '#6B7280' }}>My Templates</h3>
                {myTemplates.length === 0 ? (
                  <div className="bg-white rounded-lg shadow-md p-8 flex flex-col items-center" style={{ borderRadius: '8px' }}>
                    <div className="mb-4">
                      <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                        <rect x="15" y="20" width="50" height="40" rx="4" fill="#E5E7EB" />
                        <rect x="20" y="28" width="20" height="3" rx="1.5" fill="#6B7280" />
                        <rect x="20" y="35" width="30" height="3" rx="1.5" fill="#6B7280" />
                        <rect x="20" y="42" width="25" height="3" rx="1.5" fill="#6B7280" />
                      </svg>
                    </div>
                    <p className="text-sm mb-4 text-center" style={{ color: '#6B7280' }}>No personal templates</p>
                    <button onClick={() => navigate('/templates/extract')} className="text-sm hover:underline" style={{ color: '#2563EB' }}>
                      Create your first template
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-6">
                    {myTemplates.map((t) => (
                      <div key={t.id} className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
                        <div className="mb-4">
                          <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#2563EB20', color: '#2563EB', borderRadius: '4px' }}>
                            personal
                          </span>
                        </div>
                        <h3 className="mb-1" style={{ color: '#111827' }}>{t.name}</h3>
                        {t.description && <p className="text-sm mb-4" style={{ color: '#6B7280' }}>{t.description}</p>}
                        <div className="flex items-center gap-2 mt-4">
                          <button
                            onClick={() => navigate(`/templates/${t.id}`)}
                            className="flex-1 text-sm px-4 py-2 rounded-md text-white"
                            style={{ backgroundColor: '#2563EB', borderRadius: '6px' }}
                          >
                            Open
                          </button>
                          <button
                            onClick={() => setDeleteId(t.id)}
                            className="p-2 hover:bg-gray-100 rounded"
                            style={{ color: '#DC2626' }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md" style={{ borderRadius: '8px' }}>
            <div className="flex items-center justify-between mb-6">
              <h3 style={{ color: '#111827' }}>Create Template</h3>
              <button onClick={() => setShowCreate(false)} style={{ color: '#6B7280' }}><X size={20} /></button>
            </div>
            <div className="mb-4">
              <label className="block mb-2" style={{ color: '#111827' }}>Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Template"
                className="w-full px-3 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
            </div>
            <div className="mb-6">
              <label className="block mb-2" style={{ color: '#111827' }}>Description (optional)</label>
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Template description"
                className="w-full px-3 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowCreate(false)} className="flex-1 border rounded-md" style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', height: '44px' }}>
                Cancel
              </button>
              <button
                disabled={!newName || createMut.isPending}
                onClick={() => createMut.mutate()}
                className="flex-1 text-white rounded-md"
                style={{ backgroundColor: !newName || createMut.isPending ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px' }}
              >
                {createMut.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteId && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm" style={{ borderRadius: '8px' }}>
            <h3 className="mb-2" style={{ color: '#111827' }}>Delete template?</h3>
            <p className="mb-6" style={{ color: '#6B7280' }}>This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="flex-1 border rounded-md" style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px', height: '44px' }}>
                Cancel
              </button>
              <button
                disabled={deleteMut.isPending}
                onClick={() => deleteMut.mutate(deleteId)}
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
