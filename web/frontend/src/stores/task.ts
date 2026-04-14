import { tasksApi } from '@/api'
import type { Task, TaskCreate, TaskDetail } from '@/types'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<TaskDetail | null>(null)
  const loading = ref(false)
  const total = ref(0)

  async function fetchTasks(skip = 0, limit = 50) {
    loading.value = true
    try {
      const { data } = await tasksApi.list(skip, limit)
      tasks.value = data.tasks
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id: number) {
    loading.value = true
    try {
      const { data } = await tasksApi.get(id)
      currentTask.value = data
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: TaskCreate) {
    const res = await tasksApi.create(data)
    tasks.value.unshift(res.data)
    return res.data
  }

  async function createTaskWithUpload(formData: FormData) {
    const res = await tasksApi.createWithUpload(formData)
    tasks.value.unshift(res.data)
    return res.data
  }

  async function startTask(id: number) {
    await tasksApi.start(id)
    const task = tasks.value.find((t) => t.id === id)
    if (task) task.status = 'processing'
  }

  async function cancelTask(id: number) {
    await tasksApi.cancel(id)
    const task = tasks.value.find((t) => t.id === id)
    if (task) task.status = 'cancelled'
  }

  async function retryTask(id: number) {
    await tasksApi.retry(id)
  }

  async function deleteTask(id: number) {
    await tasksApi.delete(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
  }

  function updateTaskInList(updated: Partial<Task> & { id: number }) {
    const idx = tasks.value.findIndex((t) => t.id === updated.id)
    if (idx !== -1) {
      tasks.value[idx] = { ...tasks.value[idx], ...updated }
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    total,
    fetchTasks,
    fetchTask,
    createTask,
    createTaskWithUpload,
    startTask,
    cancelTask,
    retryTask,
    deleteTask,
    updateTaskInList,
  }
})
