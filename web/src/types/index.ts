export interface Tag {
  id: number
  name: string
  value: string
  description: string | null
  is_system: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TagCreate {
  name: string
  value: string
  description?: string
}

export interface TagUpdate {
  name?: string
  description?: string
  is_active?: boolean
}

export interface TagListResponse {
  tags: Tag[]
  total: number
}

export interface Task {
  id: number
  name: string
  status: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  total_videos: number
  processed_videos: number
  successful_videos: number
  failed_videos: number
  current_video: string | null
  max_workers: number
  progress: number
}

export interface TaskCreate {
  name: string
  video_paths?: string[]
  max_workers?: number
}

export interface TaskDetail extends Task {
  video_annotations: VideoAnnotation[]
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
}

export interface VideoAnnotation {
  id: number
  task_id: number
  file_name: string
  file_path: string
  status: string
  description: string | null
  tags: string[] | null
  duration_seconds: number | null
  is_abnormal: boolean
  abnormality_reason: string | null
  confidence_scores: Record<string, number> | null
  processing_timestamp: string | null
  error_message: string | null
}

export interface AnnotationExportResponse {
  task_id: number
  task_name: string
  total_videos_processed: number
  successful_annotations: number
  failed_annotations: number
  annotations: VideoAnnotation[]
  processing_start_time: string | null
  processing_end_time: string | null
  export_timestamp: string
}

export interface Setting {
  id: number
  key: string
  value: string | null
  encrypted: boolean
  updated_at: string
}

export interface SettingCreate {
  key: string
  value: string
}

export interface SettingUpdate {
  value: string
}

export interface SettingListResponse {
  settings: Setting[]
  total: number
}

export interface MessageResponse {
  message: string
  success: boolean
  data?: Record<string, unknown>
}

export interface WsProgressData {
  type: string
  task_id: number
  current_video?: string
  processed_videos?: number
  total_videos?: number
  successful_videos?: number
  failed_videos?: number
  progress?: number
  status?: string
  message?: string
  error?: string
  result?: Record<string, unknown>
}
