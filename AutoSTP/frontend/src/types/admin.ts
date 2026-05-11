export interface UserListItem {
  id: string
  email: string
  full_name: string
  role: 'student' | 'admin'
  is_active: boolean
  created_at: string
}

export interface UserListResponse {
  items: UserListItem[]
  total: number
  skip: number
  limit: number
}

export interface PatchUserRequest {
  role?: 'student' | 'admin'
  is_active?: boolean
}

export interface AdminStats {
  total_users: number
  total_documents: number
  total_ai_suggestions: number
}
