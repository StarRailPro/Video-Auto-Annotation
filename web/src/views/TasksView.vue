<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-h2 style="margin: 0">任务管理</n-h2>
      <n-space>
        <n-button type="primary" @click="showCreateModal = true">
          创建任务
        </n-button>
        <n-button @click="refreshTasks">
          刷新
        </n-button>
      </n-space>
    </n-space>

    <n-spin :show="taskStore.loading">
      <n-empty v-if="taskStore.tasks.length === 0 && !taskStore.loading" description="暂无任务">
        <template #extra>
          <n-button size="small" @click="showCreateModal = true">创建第一个任务</n-button>
        </template>
      </n-empty>

      <n-data-table
        v-else
        :columns="columns"
        :data="taskStore.tasks"
        :row-key="(row: Task) => row.id"
        :pagination="pagination"
        striped
      />
    </n-spin>

    <n-modal
      v-model:show="showCreateModal"
      preset="card"
      title="创建新任务"
      style="width: 600px"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="formModel" :rules="formRules" label-placement="left" label-width="100">
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="formModel.name" placeholder="输入任务名称" />
        </n-form-item>

        <n-form-item label="输入方式">
          <n-radio-group v-model:value="inputMode">
            <n-radio value="path">本地路径</n-radio>
            <n-radio value="upload">上传文件</n-radio>
          </n-radio-group>
        </n-form-item>

        <n-form-item v-if="inputMode === 'path'" label="视频路径" path="video_paths">
          <n-dynamic-input
            v-model:value="formModel.video_paths"
            placeholder="输入视频文件或文件夹路径"
          />
        </n-form-item>

        <n-form-item v-if="inputMode === 'upload'" label="上传视频">
          <n-upload
            ref="uploadRef"
            multiple
            directory-dnd
            :default-upload="false"
            @change="handleFileChange"
            accept="video/*"
          >
            <n-upload-dragger>
              <div style="padding: 20px 0">
                <n-text style="font-size: 16px">点击或拖拽视频文件到此区域</n-text>
                <n-p depth="3" style="margin: 8px 0 0 0">支持多文件上传</n-p>
              </div>
            </n-upload-dragger>
          </n-upload>
        </n-form-item>

        <n-form-item label="并发数" path="max_workers">
          <n-input-number v-model:value="formModel.max_workers" :min="1" :max="10" style="width: 100%" />
        </n-form-item>
      </n-form>

      <template #action>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="handleCreate">创建</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpace, NTag, NProgress, NPopconfirm, useMessage, useDialog } from 'naive-ui'
import type { DataTableColumns, UploadFileInfo, FormInst, FormRules } from 'naive-ui'
import { useTaskStore } from '@/stores/task'
import type { Task } from '@/types'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const taskStore = useTaskStore()

const showCreateModal = ref(false)
const creating = ref(false)
const inputMode = ref<'path' | 'upload'>('path')
const formRef = ref<FormInst | null>(null)
const uploadRef = ref<any>(null)
const uploadedFiles = ref<UploadFileInfo[]>([])

const formModel = reactive({
  name: '',
  video_paths: [''] as string[],
  max_workers: 2,
})

const formRules: FormRules = {
  name: { required: true, message: '请输入任务名称', trigger: 'blur' },
}

const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  onChange: (page: number) => { pagination.page = page },
  onUpdatePageSize: (size: number) => { pagination.page = 1; pagination.pageSize = size },
})

const statusMap: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
  pending: { type: 'default', label: '待处理' },
  processing: { type: 'info', label: '处理中' },
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'error', label: '失败' },
  cancelled: { type: 'warning', label: '已取消' },
  partial: { type: 'warning', label: '部分完成' },
}

const columns: DataTableColumns<Task> = [
  {
    title: 'ID',
    key: 'id',
    width: 60,
  },
  {
    title: '任务名称',
    key: 'name',
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const s = statusMap[row.status] ?? { type: 'default' as const, label: row.status }
      return h(NTag, { type: s.type, size: 'small', round: true }, { default: () => s.label })
    },
  },
  {
    title: '进度',
    key: 'progress',
    width: 200,
    render(row) {
      let percent = 0
      if (row.total_videos > 0) {
        percent = Math.min(Math.round((row.processed_videos / row.total_videos) * 100), 100)
      }
      const status = row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : row.status === 'processing' ? 'info' : 'default'
      return h(NProgress, {
        type: 'line',
        percentage: percent,
        status: status as 'success' | 'error' | 'info' | 'default',
        indicatorPlacement: 'inside',
      })
    },
  },
  {
    title: '视频',
    key: 'videos',
    width: 120,
    render(row) {
      return `${row.processed_videos}/${row.total_videos}`
    },
  },
  {
    title: '成功/失败',
    key: 'result',
    width: 100,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NTag, { type: 'success', size: 'small' }, { default: () => row.successful_videos }),
          h(NTag, { type: 'error', size: 'small' }, { default: () => row.failed_videos }),
        ],
      })
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 170,
    render(row) {
      return formatTime(row.created_at)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    fixed: 'right',
    render(row) {
      const buttons = [
        h(NButton, { size: 'small', tertiary: true, onClick: () => router.push(`/tasks/${row.id}`) }, { default: () => '详情' }),
      ]

      if (row.status === 'pending') {
        buttons.push(
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleStart(row.id) }, { default: () => '开始' }),
        )
      }

      if (row.status === 'processing') {
        buttons.push(
          h(NPopconfirm, { onPositiveClick: () => handleCancel(row.id) }, {
            trigger: () => h(NButton, { size: 'small', type: 'warning' }, { default: () => '取消' }),
            default: () => '确定取消此任务？',
          }),
        )
      }

      if (row.status === 'failed' || row.status === 'partial') {
        buttons.push(
          h(NButton, { size: 'small', type: 'info', onClick: () => handleRetry(row.id) }, { default: () => '重试' }),
        )
      }

      buttons.push(
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
          default: () => '确定删除此任务？此操作不可恢复。',
        }),
      )

      return h(NSpace, { size: 'small' }, { default: () => buttons })
    },
  },
]

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

function handleFileChange(data: { fileList: UploadFileInfo[] }) {
  uploadedFiles.value = data.fileList
}

async function refreshTasks() {
  await taskStore.fetchTasks()
}

async function handleStart(id: number) {
  try {
    await taskStore.startTask(id)
    message.success('任务已开始')
    await refreshTasks()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '启动任务失败')
  }
}

async function handleCancel(id: number) {
  try {
    await taskStore.cancelTask(id)
    message.success('任务已取消')
    await refreshTasks()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '取消任务失败')
  }
}

async function handleRetry(id: number) {
  try {
    await taskStore.retryTask(id)
    message.success('任务已重试')
    await refreshTasks()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '重试任务失败')
  }
}

async function handleDelete(id: number) {
  try {
    await taskStore.deleteTask(id)
    message.success('任务已删除')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '删除任务失败')
  }
}

async function handleCreate() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    if (inputMode.value === 'upload') {
      if (uploadedFiles.value.length === 0) {
        message.warning('请选择要上传的视频文件')
        return
      }
      const formData = new FormData()
      formData.append('name', formModel.name)
      formData.append('max_workers', String(formModel.max_workers))
      for (const file of uploadedFiles.value) {
        if (file.file) {
          formData.append('files', file.file)
        }
      }
      await taskStore.createTaskWithUpload(formData)
    } else {
      const paths = formModel.video_paths.filter((p) => p.trim() !== '')
      if (paths.length === 0) {
        message.warning('请输入至少一个视频路径')
        return
      }
      await taskStore.createTask({
        name: formModel.name,
        video_paths: paths,
        max_workers: formModel.max_workers,
      })
    }

    message.success('任务创建成功')
    showCreateModal.value = false
    resetForm()
    await refreshTasks()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '创建任务失败')
  } finally {
    creating.value = false
  }
}

function resetForm() {
  formModel.name = ''
  formModel.video_paths = ['']
  formModel.max_workers = 2
  uploadedFiles.value = []
  inputMode.value = 'path'
}

onMounted(() => {
  taskStore.fetchTasks()
})
</script>
