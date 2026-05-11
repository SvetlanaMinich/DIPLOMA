import { FileText, Star, FileIcon, LayoutTemplate, LogOut, Shield } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router'
import { useAuthStore } from '../../store/auth.store'

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const activeTab = location.pathname.startsWith('/templates')
    ? 'templates'
    : location.pathname.startsWith('/admin')
      ? 'admin'
      : 'documents'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'U'

  return (
    <div className="bg-white h-screen flex flex-col" style={{ width: '240px', borderRight: '1px solid #E5E7EB' }}>
      <div className="p-6 border-b" style={{ borderColor: '#E5E7EB' }}>
        <div className="flex items-center gap-2">
          <div className="relative">
            <FileText size={32} style={{ color: '#2563EB' }} />
            <Star size={14} style={{ color: '#2563EB', position: 'absolute', top: -2, right: -6 }} />
          </div>
          <span className="font-semibold" style={{ color: '#111827' }}>AutoSTP</span>
        </div>
      </div>

      <nav className="flex-1 p-4">
        <button
          onClick={() => navigate('/')}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md mb-2 transition-colors"
          style={{
            backgroundColor: activeTab === 'documents' ? '#2563EB' : 'transparent',
            color: activeTab === 'documents' ? '#FFFFFF' : '#111827',
            borderRadius: '6px',
          }}
        >
          <FileIcon size={20} />
          <span>Documents</span>
        </button>

        <button
          onClick={() => navigate('/templates')}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md mb-2 transition-colors"
          style={{
            backgroundColor: activeTab === 'templates' ? '#2563EB' : 'transparent',
            color: activeTab === 'templates' ? '#FFFFFF' : '#111827',
            borderRadius: '6px',
          }}
        >
          <LayoutTemplate size={20} />
          <span>Templates</span>
        </button>

        {user?.role === 'admin' && (
          <button
            onClick={() => navigate('/admin')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
            style={{
              backgroundColor: activeTab === 'admin' ? '#2563EB' : 'transparent',
              color: activeTab === 'admin' ? '#FFFFFF' : '#111827',
              borderRadius: '6px',
            }}
          >
            <Shield size={20} />
            <span>Admin Panel</span>
          </button>
        )}
      </nav>

      <div className="p-4 border-t" style={{ borderColor: '#E5E7EB' }}>
        <div className="flex items-center gap-3 mb-3">
          <div
            className="flex items-center justify-center text-white rounded-full"
            style={{ width: '40px', height: '40px', backgroundColor: '#2563EB' }}
          >
            {initials}
          </div>
          <div>
            <div style={{ color: '#111827' }}>{user?.full_name ?? 'User'}</div>
            <div className="text-sm" style={{ color: '#6B7280' }}>{user?.role ?? 'student'}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 border rounded-md hover:bg-gray-50 transition-colors"
          style={{ borderColor: '#E5E7EB', color: '#6B7280', borderRadius: '6px' }}
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  )
}
