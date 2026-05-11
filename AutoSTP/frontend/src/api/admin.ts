import { api } from './client'
import type { UserListResponse, PatchUserRequest, UserListItem, AdminStats } from '../types/admin'

export const listUsers = (params?: { skip?: number; limit?: number }) =>
  api.get<UserListResponse>('/admin/users', { params }).then((r) => r.data)

export const patchUser = (id: string, data: PatchUserRequest) =>
  api.patch<UserListItem>(`/admin/users/${id}`, data).then((r) => r.data)

export const getAdminStats = () =>
  api.get<AdminStats>('/admin/stats').then((r) => r.data)
