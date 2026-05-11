export type TemplateType = 'system' | 'personal'

export interface TemplateOut {
  id: string
  user_id: string
  name: string
  description: string
  type: TemplateType
  template_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TemplateListResponse {
  items: TemplateOut[]
  total: number
}

export interface TemplateCreate {
  name: string
  description?: string
  template_json: Record<string, unknown>
  type?: 'personal'
}

export interface TemplateUpdate {
  name?: string
  description?: string
  template_json?: Record<string, unknown>
}
