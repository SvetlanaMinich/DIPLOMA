import { api } from './client'
import type { TemplateOut, TemplateListResponse, TemplateCreate, TemplateUpdate } from '../types/template'

export const listTemplates = (params?: { skip?: number; limit?: number; type_filter?: string }) =>
  api.get<TemplateListResponse>('/templates', { params }).then((r) => r.data)

export const getTemplate = (id: string) =>
  api.get<TemplateOut>(`/templates/${id}`).then((r) => r.data)

export const createTemplate = (data: TemplateCreate) =>
  api.post<TemplateOut>('/templates', data).then((r) => r.data)

export const updateTemplate = (id: string, data: TemplateUpdate) =>
  api.put<TemplateOut>(`/templates/${id}`, data).then((r) => r.data)

export const deleteTemplate = (id: string) =>
  api.delete(`/templates/${id}`).then((r) => r.data)

export const extractTemplate = (file: File, name?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  return api.post<TemplateOut>('/templates/extract', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  }).then((r) => r.data)
}

export const extractTemplateOnly = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/templates/extract-only', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  }).then((r) => r.data)
}
