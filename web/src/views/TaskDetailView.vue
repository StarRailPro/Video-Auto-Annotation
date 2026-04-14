<template>
  <div>
    <n-spin :show="taskStore.loading">
      <template v-if="task">
        <n-page-header @back="router.push('/tasks')" title="任务详情" :subtitle="task.name">
          <template #extra>
            <n-space>
              <n-button v-if="task.status === 'pending'" type="primary" @click="handleStart" :loading="actionLoading">开始处理</n-button>
              <n-button v-if="task.status === 'processing'" type="warning" @click="handleCancel" :loading="actionLoading">取消任务</n-button>
              <n-button v-if="task.status === 'failed' || task.status === 'partial'" type="info" @click="handleRetry" :loading="actionLoading">重试失败项</n-button>
              <n-button v-if="task.status === 'completed' || task.status === 'partial'" @click="handleDownload">下载标注</n-button>
              <n-button @click="refreshDetail">刷新</n-button>
            </n-space>
          </template>
        </n-page-header>

        <n-grid :cols="4" :x-gap="16" :y-gap="16" style="margin-top: 16px">
          <n-gi>
            <n-card size="small">
              <n-statistic label="状态">
                <template #default>
                  <n-tag :type="statusMap[task.status]?.type ?? 'default'" round>
                    {{ statusMap[task.status]?.label ?? task.status }}
                  </n-tag>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card size="small">
              <n-statistic label="总视频数" :value="displayTotalVideos" />
            </n-card>
          </n-gi>
          <n-gi>
            <n-card size="small">
              <n-statistic label="成功">
                <template #default>
                  <n-text type="success">{{ displaySuccessfulVideos }}</n-text>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card size="small">
              <n-statistic label="失败">
                <template #default>
                  <n-text type="error">{{ displayFailedVideos }}</n-text>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
        </n-grid>

        <n-card title="处理进度" style="margin-top: 16px">
          <n-space vertical :size="12">
            <n-progress
              type="line"
              :percentage="progressPercent"
              :status="progressStatus"
              indicator-placement="inside"
              :height="24"
            />
            <n-space justify="space-between">
              <n-text depth="3">
                {{ displayProcessedVideos }} / {{ displayTotalVideos }} 已处理
              </n-text>
              <n-text v-if="displayCurrentVideo" depth="3">
                当前处理: {{ displayCurrentVideo }}
              </n-text>
            </n-space>
            <n-space>
              <n-tag :type="wsConnected ? 'success' : 'default'" size="small">
                {{ wsConnected ? '实时连接中' : '未连接实时更新' }}
              </n-tag>
              <n-tag v-if="retryingHint" type="warning" size="small">
                {{ retryingHint }}
              </n-tag>
            </n-space>
          </n-space>
        </n-card>

        <n-card title="任务信息" style="margin-top: 16px">
          <n-descriptions :column="2" bordered label-placement="left">
            <n-descriptions-item label="任务ID">{{ task.id }}</n-descriptions-item>
            <n-descriptions-item label="任务名称">{{ task.name }}</n-descriptions-item>
            <n-descriptions-item label="并发数">{{ task.max_workers }}</n-descriptions-item>
            <n-descriptions-item label="创建时间">{{ formatTime(task.created_at) }}</n-descriptions-item>
            <n-descriptions-item label="开始时间">{{ formatTime(task.started_at) }}</n-descriptions-item>
            <n-descriptions-item label="完成时间">{{ formatTime(task.completed_at) }}</n-descriptions-item>
          </n-descriptions>
        </n-card>

        <n-card title="视频标注列表" style="margin-top: 16px">
          <template #header-extra>
            <n-space>
              <n-radio-group v-model:value="videoFilter" size="small">
                <n-radio-button value="all">全部</n-radio-button>
                <n-radio-button value="completed">已完成</n-radio-button>
                <n-radio-button value="failed">失败</n-radio-button>
                <n-radio-button value="pending">待处理</n-radio-button>
              </n-radio-group>
            </n-space>
          </template>

          <n-empty v-if="filteredAnnotations.length === 0" description="暂无标注数据" />
          <n-list v-else bordered>
            <n-list-item v-for="item in filteredAnnotations" :key="item.id">
              <n-thing>
                <template #header>
                  <n-space align="center">
                    <n-text>{{ item.file_name }}</n-text>
                    <n-tag :type="videoStatusMap[item.status]?.type ?? 'default'" size="small" round>
                      {{ videoStatusMap[item.status]?.label ?? item.status }}
                    </n-tag>
                    <n-tag v-if="item.is_abnormal" type="error" size="small">异常</n-tag>
                  </n-space>
                </template>
                <template #header-extra>
                  <n-button text type="primary" @click="showAnnotationDetail(item)">查看详情</n-button>
                </template>
                <template #description>
                  <n-space vertical size="small">
                    <n-text v-if="item.description" depth="3">{{ item.description }}</n-text>
                    <n-space v-if="item.tags && item.tags.length > 0" size="small">
                      <n-tag v-for="tag in item.tags" :key="tag" size="small" type="info">{{ tag }}</n-tag>
                    </n-space>
                    <n-text v-if="item.error_message" type="error">错误: {{ item.error_message }}</n-text>
                    <n-text v-if="item.duration_seconds" depth="3">时长: {{ item.duration_seconds.toFixed(1) }}s</n-text>
                  </n-space>
                </template>
              </n-thing>
            </n-list-item>
          </n-list>
        </n-card>
      </template>

      <n-result v-else-if="!taskStore.loading" status="404" title="任务不存在" description="该任务可能已被删除">
        <template #footer>
          <n-button @click="router.push('/tasks')">返回任务列表</n-button>
        </template>
      </n-result>
    </n-spin>

    <n-modal
      v-model:show="showDetailModal"
      preset="card"
      title="标注详情"
      style="width: 700px"
    >
      <template v-if="selectedAnnotation">
        <n-descriptions :column="1" bordered label-placement="left">
          <n-descriptions-item label="文件名">{{ selectedAnnotation.file_name }}</n-descriptions-item>
          <n-descriptions-item label="文件路径">{{ selectedAnnotation.file_path }}</n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="videoStatusMap[selectedAnnotation.status]?.type ?? 'default'" size="small">
              {{ videoStatusMap[selectedAnnotation.status]?.label ?? selectedAnnotation.status }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="描述">{{ selectedAnnotation.description ?? '-' }}</n-descriptions-item>
          <n-descriptions-item label="标签">
            <n-space v-if="selectedAnnotation.tags && selectedAnnotation.tags.length > 0" size="small">
              <n-tag v-for="tag in selectedAnnotation.tags" :key="tag" size="small" type="info">{{ tag }}</n-tag>
            </n-space>
            <n-text v-else depth="3">无</n-text>
          </n-descriptions-item>
          <n-descriptions-item label="是否异常">
            <n-tag :type="selectedAnnotation.is_abnormal ? 'error' : 'success'" size="small">
              {{ selectedAnnotation.is_abnormal ? '异常' : '正常' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item v-if="selectedAnnotation.abnormality_reason" label="异常原因">
            {{ selectedAnnotation.abnormality_reason }}
          </n-descriptions-item>
          <n-descriptions-item label="时长">
            {{ selectedAnnotation.duration_seconds ? selectedAnnotation.duration_seconds.toFixed(1) + 's' : '-' }}
          </n-descriptions-item>
          <n-descriptions-item v-if="selectedAnnotation.confidence_scores" label="置信度">
            <n-space vertical size="small">
              <n-space v-for="(score, key) in selectedAnnotation.confidence_scores" :key="key" size="small" align="center">
                <n-text style="min-width: 80px">{{ key }}</n-text>
                <n-progress type="line" :percentage="Math.round(score * 100)" :show-indicator="true" style="width: 200px" />
              </n-space>
            </n-space>
          </n-descriptions-item>
          <n-descriptions-item label="处理时间">{{ formatTime(selectedAnnotation.processing_timestamp) }}</n-descriptions-item>
          <n-descriptions-item v-if="selectedAnnotation.error_message" label="错误信息">
            <n-text type="error">{{ selectedAnnotation.error_message }}</n-text>
          </n-descriptions-item>
        </n-descriptions>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useTaskStore } from '@/stores/task'
import { useWebSocket } from '@/composables/useWebSocket'
import { annotationsApi } from '@/api'
import type { VideoAnnotation, WsProgressData } from '@/types'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const taskStore = useTaskStore()

const taskId = computed(() => Number(route.params.id))
const task = computed(() => taskStore.currentTask)

const videoFilter = ref<'all' | 'completed' | 'failed' | 'pending'>('all')
const showDetailModal = ref(false)
const selectedAnnotation = ref<VideoAnnotation | null>(null)
const actionLoading = ref(false)
const retryingHint = ref('')
let lastRefreshTime = 0
const REFRESH_THROTTLE_MS = 2000

const { connected: wsConnected, lastData: wsProgress, connect, disconnect } = useWebSocket(taskId.value)

const statusMap: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
  pending: { type: 'default', label: '待处理' },
  processing: { type: 'info', label: '处理中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  cancelled: { type: 'warning', label: '已取消' },
  partial: { type: 'warning', label: '部分完成' },
}

const videoStatusMap: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
  pending: { type: 'default', label: '待处理' },
  processing: { type: 'info', label: '处理中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  skipped: { type: 'warning', label: '已跳过' },
}

const displayTotalVideos = computed(() => {
  if (wsProgress.value?.total_videos !== undefined && wsProgress.value.total_videos > 0) {
    return wsProgress.value.total_videos
  }
  return task.value?.total_videos ?? 0
})

const displayProcessedVideos = computed(() => {
  if (wsProgress.value?.processed_videos !== undefined) {
    return wsProgress.value.processed_videos
  }
  return task.value?.processed_videos ?? 0
})

const displaySuccessfulVideos = computed(() => {
  if (wsProgress.value?.successful_videos !== undefined) {
    return wsProgress.value.successful_videos
  }
  return task.value?.successful_videos ?? 0
})

const displayFailedVideos = computed(() => {
  if (wsProgress.value?.failed_videos !== undefined) {
    return wsProgress.value.failed_videos
  }
  return task.value?.failed_videos ?? 0
})

const displayCurrentVideo = computed(() => {
  if (wsProgress.value?.current_video !== undefined) {
    return wsProgress.value.current_video
  }
  return task.value?.current_video ?? null
})

const progressPercent = computed(() => {
  const total = displayTotalVideos.value
  const processed = displayProcessedVideos.value
  if (total <= 0) return 0
  return Math.min(Math.round((processed / total) * 100), 100)
})

const progressStatus = computed(() => {
  if (!task.value) return 'default' as const
  if (task.value.status === 'completed') return 'success' as const
  if (task.value.status === 'failed') return 'error' as const
  if (task.value.status === 'processing') return 'info' as const
  return 'default' as const
})

const filteredAnnotations = computed(() => {
  if (!task.value?.video_annotations) return []
  const list = task.value.video_annotations
  switch (videoFilter.value) {
    case 'completed': return list.filter((a) => a.status === 'completed')
    case 'failed': return list.filter((a) => a.status === 'failed')
    case 'pending': return list.filter((a) => a.status === 'pending' || a.status === 'processing')
    default: return list
  }
})

function formatTime(iso: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

function showAnnotationDetail(item: VideoAnnotation) {
  selectedAnnotation.value = item
  showDetailModal.value = true
}

async function refreshDetail() {
  const now = Date.now()
  if (now - lastRefreshTime < REFRESH_THROTTLE_MS) return
  lastRefreshTime = now
  await taskStore.fetchTask(taskId.value)
}

async function handleStart() {
  actionLoading.value = true
  try {
    await taskStore.startTask(taskId.value)
    message.success('任务已开始')
    await refreshDetail()
    connect()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '启动任务失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleCancel() {
  actionLoading.value = true
  try {
    await taskStore.cancelTask(taskId.value)
    message.warning('任务取消请求已发送')
    disconnect()
    await refreshDetail()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '取消任务失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleRetry() {
  actionLoading.value = true
  try {
    await taskStore.retryTask(taskId.value)
    message.success('重试已开始')
    await refreshDetail()
    connect()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '重试失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleDownload() {
  try {
    const res = await annotationsApi.download(taskId.value)
    const blob = new Blob([res.data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotations_task_${taskId.value}.json`
    a.click()
    URL.revokeObjectURL(url)
    message.success('下载成功')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '下载失败')
  }
}

watch(wsProgress, (data: WsProgressData | null) => {
  if (!data || !task.value) return

  if (data.message) {
    if (data.message.includes('retry') || data.message.includes('重试')) {
      retryingHint.value = data.message
    } else {
      retryingHint.value = ''
    }
  }

  if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled' || data.status === 'partial') {
    retryingHint.value = ''
    refreshDetail()
    return
  }

  if (data.total_videos !== undefined && data.total_videos > 0) {
    task.value.total_videos = data.total_videos
  }
  if (data.processed_videos !== undefined) {
    task.value.processed_videos = data.processed_videos
  }
  if (data.successful_videos !== undefined) {
    task.value.successful_videos = data.successful_videos
  }
  if (data.failed_videos !== undefined) {
    task.value.failed_videos = data.failed_videos
  }
  if (data.current_video !== undefined) {
    task.value.current_video = data.current_video
  }
  if (data.status !== undefined) {
    task.value.status = data.status
  }

  if (data.processed_videos !== undefined) {
    refreshDetail()
  }
})

onMounted(async () => {
  await taskStore.fetchTask(taskId.value)
  if (task.value?.status === 'processing') {
    connect()
  }
})

onUnmounted(() => {
  disconnect()
})
</script>
