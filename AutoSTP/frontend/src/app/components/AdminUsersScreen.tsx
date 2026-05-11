import { Search, ChevronDown } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { listUsers, patchUser } from '../../api/admin'
import { useDebounce } from '../../hooks/useDebounce'

const PAGE_SIZE = 10

export function AdminUsersScreen() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const debouncedSearch = useDebounce(search, 300)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, debouncedSearch],
    queryFn: () => listUsers({ skip: page * PAGE_SIZE, limit: PAGE_SIZE }),
  })

  const patchMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { role?: 'student' | 'admin'; is_active?: boolean } }) =>
      patchUser(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
    onError: () => toast.error('Failed to update user'),
  })

  const users = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const filteredUsers = debouncedSearch
    ? users.filter((u) => u.email.toLowerCase().includes(debouncedSearch.toLowerCase()) || u.full_name.toLowerCase().includes(debouncedSearch.toLowerCase()))
    : users

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <h1 className="mb-6" style={{ color: '#111827' }}>Admin Panel</h1>

          <div className="flex gap-8 mb-6 border-b" style={{ borderColor: '#E5E7EB' }}>
            <button className="pb-4 border-b-2" style={{ borderColor: '#2563EB', color: '#2563EB' }}>Users</button>
            <button onClick={() => navigate('/admin/statistics')} className="pb-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Statistics</button>
          </div>

          <div className="mb-6">
            <div className="relative" style={{ width: '400px' }}>
              <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#6B7280' }} />
              <input
                type="text"
                placeholder="Search by email or name..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(0) }}
                className="w-full pl-10 pr-4 py-2 border rounded-md"
                style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md overflow-hidden" style={{ borderRadius: '8px' }}>
            <table className="w-full">
              <thead style={{ backgroundColor: '#F8FAFC' }}>
                <tr>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Email</th>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Full Name</th>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Role</th>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Status</th>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Registered</th>
                  <th className="text-left px-6 py-4" style={{ color: '#6B7280' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-t" style={{ borderColor: '#E5E7EB' }}>
                      {Array.from({ length: 6 }).map((__, j) => (
                        <td key={j} className="px-6 py-4">
                          <div className="h-4 rounded animate-pulse" style={{ backgroundColor: '#E5E7EB' }} />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : filteredUsers.map((user) => (
                  <tr key={user.id} className="border-t" style={{ borderColor: '#E5E7EB' }}>
                    <td className="px-6 py-4" style={{ color: '#111827' }}>{user.email}</td>
                    <td className="px-6 py-4" style={{ color: '#111827' }}>{user.full_name}</td>
                    <td className="px-6 py-4">
                      <span
                        className="px-2 py-1 rounded text-xs"
                        style={{ backgroundColor: user.role === 'admin' ? '#2563EB20' : '#6B728020', color: user.role === 'admin' ? '#2563EB' : '#6B7280', borderRadius: '4px' }}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className="px-2 py-1 rounded text-xs"
                        style={{ backgroundColor: user.is_active ? '#16A34A20' : '#DC262620', color: user.is_active ? '#16A34A' : '#DC2626', borderRadius: '4px' }}
                      >
                        {user.is_active ? 'Active' : 'Blocked'}
                      </span>
                    </td>
                    <td className="px-6 py-4" style={{ color: '#6B7280' }}>{new Date(user.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="relative">
                          <select
                            className="appearance-none border rounded-md px-3 py-1 pr-8 text-sm"
                            style={{ borderColor: '#E5E7EB', borderRadius: '6px', color: '#111827' }}
                            value={user.role}
                            onChange={(e) => patchMut.mutate({ id: user.id, payload: { role: e.target.value as 'student' | 'admin' } })}
                          >
                            <option value="student">student</option>
                            <option value="admin">admin</option>
                          </select>
                          <ChevronDown size={16} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#6B7280' }} />
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={user.is_active}
                            onChange={(e) => patchMut.mutate({ id: user.id, payload: { is_active: e.target.checked } })}
                          />
                          <div
                            className="w-11 h-6 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"
                            style={{ backgroundColor: user.is_active ? '#16A34A' : '#6B7280' }}
                          />
                        </label>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 border rounded-md"
                style={{ borderColor: '#E5E7EB', color: page === 0 ? '#6B7280' : '#111827', borderRadius: '6px', opacity: page === 0 ? 0.5 : 1 }}
              >
                Previous
              </button>
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  onClick={() => setPage(i)}
                  className="px-3 py-1 rounded-md"
                  style={{ backgroundColor: page === i ? '#2563EB' : 'transparent', color: page === i ? '#FFFFFF' : '#111827', border: page === i ? 'none' : '1px solid #E5E7EB', borderRadius: '6px' }}
                >
                  {i + 1}
                </button>
              ))}
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 border rounded-md"
                style={{ borderColor: '#E5E7EB', color: page >= totalPages - 1 ? '#6B7280' : '#111827', borderRadius: '6px', opacity: page >= totalPages - 1 ? 0.5 : 1 }}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
