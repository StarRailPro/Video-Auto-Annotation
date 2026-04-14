<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-h2 style="margin: 0">标注预览</n-h2>
      <n-space>
        <n-select
          v-model:value="selectedTaskId"
          :options="taskOptions"
          placeholder="选择任务"
          style="width: 260px"
          clearable
          @update:value="handleTaskChange"
        />
        <n-button :disabled="!selectedTaskId" @click="handleDownloadAll">批量下载 JSON</n-button>
      </n-space>
    </n-space>

    <n-spin :show="loading">
      <n-empty v-if="!selectedTaskId" description="请选择一个任务查看标注数据" />
      <n-empty v-else-if="annotations.length === 0 && !loading" description="该任务暂无标注数据" />
      <template v-else-if="annotations.length > 0">
        <n-space style="margin-bottom: 16px">
          <n-statistic label="总标注数" :value="annotations.length" />
          <n-statistic label="已完成">
            <template #default>
              <n-text type="success">{{ completedCount }}</n-text>
            </template>
          </n-statistic>
          <n-statistic label="失败">
            <template #default>
              <n-text type="error">{{ failedCount }}</n-text>
            </template>
          </n-statistic>
          <n-statistic label="异常视频">
            <template #default>
              <n-text type="warning">{{ abnormalCount }}</n-text>
            </template>
          </n-statistic>
        </n-space>

        <n-grid :cols="1" :y-gap="12">
          <n-gi v-for="item in annotations" :key="item.id">
            <n-card size="small" hoverable>
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
                <n-button text type="primary" @click="showDetail(item)">详情</n-button>
              </template>
              <n-space vertical size="small">
                <n-text v-if="item.description" depth="2">{{ item.description }}</n-text>
                <n-space v-if="item.tags && item.tags.length > 0" size="small">
                  <n-tag v-for="tag in item.tags" :key="tag" size="small" type="info" round>{{ tag }}</n-tag>
                </n-space>
                <n-space size="large">
                  <n-text v-if="item.duration_seconds" depth="3">时长: {{ item.duration_seconds.toFixed(1) }}s</n-text>
                  <n-text v-if="item.processing_timestamp" depth="3">处理时间: {{ formatTime(item.processing_timestamp) }}</n-text>
                </n-space>
                <n-text v-if="item.error_message" type="error">错误: {{ item.error_message }}</n-text>
                <template v-if="item.confidence_scores">
                  <n-divider style="margin: 4px 0" />
                  <n-space vertical size="small">
                    <n-text depth="3" style="font-size: 12px">置信度:</n-text>
                    <n-space v-for="(score, key) in item.confidence_scores" :key="key" size="small" align="center">
                      <n-text style="min-width: 80px; font-size: 12px">{{ key }}</n-text>
                      <n-progress type="line" :percentage="Math.round(score * 100)" :show-indicator="true" style="width: 160px" :height="14" />
                    </n-space>
                  </n-space>
                </template>
              </n-space>
            </n-card>
          </n-gi>
        </n-grid>
      </template>
    </n-spin>

    <n-modal v-model:show="showDetailModal" preset="card" title="标注详情" style="width: 700px">
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
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { annotationsApi, tasksApi } from '@/api'
import type { VideoAnnotation, Task } from '@/types'

const message = useMessage()

const loading = ref(false)
const annotations = ref<VideoAnnotation[]>([])
const selectedTaskId = ref<number | null>(null)
const taskList = ref<Task[]>([])
const showDetailModal = ref(false)
const selectedAnnotation = ref<VideoAnnotation | null>(null)

const taskOptions = computed(() =>
  taskList.value.map((t) => ({ label: `${t.name} (${t.status})`, value: t.id }))
)

const completedCount = computed(() => annotations.value.filter((a) => a.status === 'completed').length)
const failedCount = computed(() => annotations.value.filter((a) => a.status === 'failed').length)
const abnormalCount = computed(() => annotations.value.filter((a) => a.is_abnormal).length)

const videoStatusMap: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
  pending: { type: 'default', label: '待处理' },
  processing: { type: 'info', label: '处理中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  skipped: { type: 'warning', label: '已跳过' },
}

function formatTime(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function showDetail(item: VideoAnnotation) {
  selectedAnnotation.value = item
  showDetailModal.value = true
}

async function handleTaskChange(taskId: number | null) {
  if (!taskId) {
    annotations.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await annotationsApi.list(taskId)
    annotations.value = data
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '获取标注数据失败')
  } finally {
    loading.value = false
  }
}

async function handleDownloadAll() {
  if (!selectedTaskId.value) return
  try {
    const res = await annotationsApi.download(selectedTaskId.value)
    const blob = new Blob([res.data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotations_task_${selectedTaskId.value}.json`
    a.click()
    URL.revokeObjectURL(url)
    message.success('下载成功')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '下载失败')
  }
}

onMounted(async () => {
  try {
    const { data } = await tasksApi.list()
    taskList.value = data.tasks
  } catch {
    // ignore
  }
})
</script>
