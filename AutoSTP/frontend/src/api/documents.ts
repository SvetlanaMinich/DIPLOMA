import { api } from './client'
import type {
  DocumentDetail,
  DocumentListResponse,
  DocumentSnapshot,
  SegmentResponse,
  HintsResponse,
} from '../types/document'

export const uploadDocument = (file: File, title?: string, document_type = 'ku') => {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  form.append('document_type', document_type)
  return api.post<DocumentDetail>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const listDocuments = (params?: { skip?: number; limit?: number; title_contains?: string }) =>
  api.get<DocumentListResponse>('/documents', { params }).then((r) => r.data)

export const getDocument = (id: string) =>
  api.get<DocumentDetail>(`/documents/${id}`).then((r) => r.data)

export const updateDocument = (id: string, payload: { title?: string; snapshot: DocumentSnapshot }) =>
  api.put<DocumentDetail>(`/documents/${id}`, payload).then((r) => r.data)

export const deleteDocument = (id: string) =>
  api.delete(`/documents/${id}`).then((r) => r.data)

export const segmentDocument = (id: string, template_id: string) =>
  api.post<SegmentResponse>(`/documents/${id}/segment`, { template_id }).then((r) => r.data)

export const formatDocument = (id: string, template_id: string) =>
  api.post<DocumentDetail>(`/documents/${id}/format`, { template_id }).then((r) => r.data)

export const getHints = (docId: string, sectionId: string) =>
  api.post<HintsResponse>(`/documents/${docId}/sections/${sectionId}/hints`).then((r) => r.data)

export const exportDocx = async (id: string, filename = 'document.docx') => {
  const res = await api.get(`/documents/${id}/export/docx`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const exportPdf = async (id: string, filename = 'document.pdf') => {
  const res = await api.get(`/documents/${id}/export/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
