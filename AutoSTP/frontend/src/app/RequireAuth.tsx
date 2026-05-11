import { Navigate, Outlet } from 'react-router'
import { useAuthStore } from '../store/auth.store'

export function RequireAuth() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated())
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Outlet />
}
