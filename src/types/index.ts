export interface ApiModule {
  id: string
  name: string
  display_name: string
  description: string
  endpoint_count: number
  color: string
  created_at: string
}

export interface ApiEndpoint {
  id: string
  module_id: string
  path: string
  method: string
  description: string
  query_params: Record<string, unknown>
  headers: Record<string, unknown>
  body_schema: Record<string, unknown>
  response_schema: Record<string, unknown>
  is_active: boolean
  created_at: string
  module?: ApiModule
}

export interface ApiTestHistory {
  id: string
  endpoint_id: string
  base_url: string
  full_url: string
  method: string
  request_headers: Record<string, unknown>
  request_body: Record<string, unknown>
  response_status: number | null
  response_body: Record<string, unknown>
  response_headers: Record<string, unknown>
  duration_ms: number | null
  error_message: string | null
  created_at: string
}

export interface ApiEnvironment {
  id: string
  name: string
  base_url: string
  description: string
  is_active: boolean
  created_at: string
}

export interface UploadedFile {
  id: string
  filename: string
  file_type: string
  file_size: number
  storage_path: string
  description: string | null
  metadata: Record<string, unknown>
  created_at: string
}
