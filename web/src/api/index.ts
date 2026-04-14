import axios from 'axios'
import type {
  TagListResponse,
  Tag,
  TagCreate,
  TagUpdate,
  MessageResponse,
  TaskListResponse,
  Task,
  TaskCreate,
  TaskDetail,
  VideoAnnotation,
  AnnotationExportResponse,
  SettingListResponse,
  Setting,
  SettingCreate,
  SettingUpdate,
} from '@/types'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Tags
export const tagsApi = {
  list: (activeOnly = false) =>
    http.get<TagListResponse>('/tags', { params: { active_only: activeOnly } }),
  get: (id: number) => http.get<Tag>(`/tags/${id}`),
  create: (data: TagCreate) => http.post<Tag>('/tags', data),
  update: (id: number, data: TagUpdate) => http.put<Tag>(`/tags/${id}`, data),
  delete: (id: number) => http.delete<MessageResponse>(`/tags/${id}`),
  activeValues: () => http.get<MessageResponse>('/tags/values/active'),
}

// Tasks
export const tasksApi = {
  list: (skip = 0, limit = 50) =>
    http.get<TaskListResponse>('/tasks', { params: { skip, limit } }),
  get: (id: number) => http.get<TaskDetail>(`/tasks/${id}`),
  create: (data: TaskCreate) => http.post<Task>('/tasks', data),
  createWithUpload: (formData: FormData) =>
    http.post<Task>('/tasks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  start: (id: number) => http.post<MessageResponse>(`/tasks/${id}/start`),
  cancel: (id: number) => http.post<MessageResponse>(`/tasks/${id}/cancel`),
  retry: (id: number) => http.post<Task>(`/tasks/${id}/retry`),
  delete: (id: number) => http.delete<MessageResponse>(`/tasks/${id}`),
}

// Annotations
export const annotationsApi = {
  list: (taskId: number) =>
    http.get<VideoAnnotation[]>(`/annotations/task/${taskId}`),
  summary: (taskId: number) =>
    http.get<AnnotationExportResponse>(`/annotations/task/${taskId}/summary`),
  download: (taskId: number) =>
    http.get(`/annotations/task/${taskId}/download`, { responseType: 'blob' }),
  get: (id: number) => http.get<VideoAnnotation>(`/annotations/video/${id}`),
}

// Settings
export const settingsApi = {
  list: () => http.get<SettingListResponse>('/settings'),
  get: (key: string) => http.get<Setting>(`/settings/${key}`),
  create: (data: SettingCreate) => http.post<Setting>('/settings', data),
  update: (key: string, data: SettingUpdate) =>
    http.put<Setting>(`/settings/${key}`, data),
  delete: (key: string) => http.delete<MessageResponse>(`/settings/${key}`),
  testApiKey: () => http.post<MessageResponse>('/settings/api-key/test'),
}

// Health
export const healthApi = {
  check: () => http.get<{ status: string; message: string }>('/health'),
}
