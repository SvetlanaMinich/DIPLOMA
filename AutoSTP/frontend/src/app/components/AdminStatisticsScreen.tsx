import { Users, FileText, Zap } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Sidebar } from './Sidebar'
import { getAdminStats } from '../../api/admin'

export function AdminStatisticsScreen() {
  const navigate = useNavigate()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: getAdminStats,
  })

  const statCards = [
    { icon: Users, label: 'Users', value: stats?.total_users ?? 0, color: '#2563EB' },
    { icon: FileText, label: 'Documents', value: stats?.total_documents ?? 0, color: '#16A34A' },
    { icon: Zap, label: 'AI Requests', value: stats?.total_ai_suggestions ?? 0, color: '#D97706' },
  ]

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <h1 className="mb-6" style={{ color: '#111827' }}>Admin Panel</h1>

          <div className="flex gap-8 mb-8 border-b" style={{ borderColor: '#E5E7EB' }}>
            <button onClick={() => navigate('/admin')} className="pb-4 border-b-2 border-transparent hover:border-gray-300" style={{ color: '#6B7280' }}>Users</button>
            <button className="pb-4 border-b-2" style={{ borderColor: '#2563EB', color: '#2563EB' }}>Statistics</button>
          </div>

          <div className="grid grid-cols-3 gap-6 mb-8">
            {statCards.map((stat, index) => {
              const Icon = stat.icon
              return (
                <div key={index} className="bg-white rounded-lg shadow-md p-6" style={{ borderRadius: '8px' }}>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="p-3 rounded-lg" style={{ backgroundColor: stat.color + '20' }}>
                      <Icon size={24} style={{ color: stat.color }} />
                    </div>
                    <span style={{ color: '#6B7280' }}>{stat.label}</span>
                  </div>
                  {isLoading ? (
                    <div className="h-9 w-24 rounded animate-pulse" style={{ backgroundColor: '#E5E7EB' }} />
                  ) : (
                    <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#111827' }}>{stat.value}</div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="bg-white rounded-lg shadow-md p-8" style={{ borderRadius: '8px' }}>
            <h3 className="mb-6" style={{ color: '#111827' }}>Daily Activity</h3>
            <div className="border-2 border-dashed rounded-lg flex items-center justify-center" style={{ borderColor: '#E5E7EB', height: '400px', borderRadius: '8px' }}>
              <div className="text-center">
                <div className="mb-2" style={{ color: '#6B7280', fontSize: '48px' }}>📊</div>
                <p style={{ color: '#6B7280' }}>Daily activity — coming soon</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
