export type DocumentType = 'ku' | 'di'
export type DocumentStatus = 'uploaded' | 'inpr' | 'formatted'

export interface DocumentSnapshot {
  plain_text: string
  nodes: unknown[]
}

export interface DocumentVersion {
  version_string: string
  snapshot: DocumentSnapshot
  created_at: string
}

export interface DocumentMetadata {
  stored_file_format: string
  upload_extension: string
  stored_filename: string
  storage_dir: string
}

export interface DocumentListItem {
  id: string
  title: string
  document_type: DocumentType
  status: DocumentStatus
  created_at: string
  updated_at: string
  original_filename?: string
}

export interface DocumentDetail extends DocumentListItem {
  current_version: DocumentVersion
  versions_count: number
  metadata: DocumentMetadata
}

export interface DocumentListResponse {
  items: DocumentListItem[]
  total: number
  skip: number
  limit: number
}

export interface SectionOut {
  id: string
  role: string
  title: string
  level: number
  order_number: number
  text_preview: string
  char_count: number
}

export interface SegmentResponse {
  document_id: string
  template_id: string
  sections: SectionOut[]
  total_sections: number
  unmatched_chars: number
}

export interface HintsResponse {
  section_id: string
  hints: string[]
}
