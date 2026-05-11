import { useEffect } from 'react'
import { useAuthStore } from '../store/auth.store'
import { getMe } from '../api/auth'

export function useInitUser() {
  const { accessToken, user, setAuth, refreshToken, logout } = useAuthStore()

  useEffect(() => {
    if (accessToken && !user) {
      getMe()
        .then((me) => setAuth(me, accessToken, refreshToken ?? ''))
        .catch(() => logout())
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
}
