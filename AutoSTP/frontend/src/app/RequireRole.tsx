import { Navigate, Outlet } from 'react-router'
import { useAuthStore } from '../store/auth.store'

export function RequireRole({ role }: { role: string }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to="/" replace />
  return <Outlet />
}
