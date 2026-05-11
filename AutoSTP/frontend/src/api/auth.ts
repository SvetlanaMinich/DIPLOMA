import { api } from './client'
import type { LoginRequest, RegisterRequest, TokenResponse, UserMe } from '../types/auth'

export const login = (data: LoginRequest) =>
  api.post<TokenResponse>('/auth/login', data).then((r) => r.data)

export const register = (data: RegisterRequest) =>
  api.post<UserMe>('/auth/register', data).then((r) => r.data)

export const refresh = (refresh_token: string) =>
  api.post<TokenResponse>('/auth/refresh', { refresh_token }).then((r) => r.data)

export const logout = (refresh_token: string) =>
  api.post('/auth/logout', { refresh_token }).then((r) => r.data)

export const getMe = () =>
  api.get<UserMe>('/auth/me').then((r) => r.data)
