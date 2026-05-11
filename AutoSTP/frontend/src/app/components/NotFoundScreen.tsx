import { useNavigate } from 'react-router'

export function NotFoundScreen() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col items-center justify-center" style={{ backgroundColor: '#F8FAFC' }}>
      <div style={{ fontSize: '72px', color: '#E5E7EB', fontWeight: 700, lineHeight: 1 }}>404</div>
      <p className="mt-4 mb-8" style={{ color: '#6B7280', fontSize: '18px' }}>Page not found</p>
      <button
        onClick={() => navigate('/')}
        className="px-6 py-2 text-white rounded-md"
        style={{ backgroundColor: '#2563EB', borderRadius: '6px' }}
      >
        Back to Dashboard
      </button>
    </div>
  )
}
