export interface UserMe {
  id: string
  email: string
  full_name: string
  role: 'student' | 'admin'
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
}
