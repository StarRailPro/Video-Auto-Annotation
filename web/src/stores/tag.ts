import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tagsApi } from '@/api'
import type { Tag, TagCreate, TagUpdate } from '@/types'

export const useTagStore = defineStore('tag', () => {
  const tags = ref<Tag[]>([])
  const loading = ref(false)

  async function fetchTags(activeOnly = false) {
    loading.value = true
    try {
      const { data } = await tagsApi.list(activeOnly)
      tags.value = data.tags
    } finally {
      loading.value = false
    }
  }

  async function createTag(tagData: TagCreate) {
    const { data } = await tagsApi.create(tagData)
    tags.value.push(data)
    return data
  }

  async function updateTag(id: number, tagData: TagUpdate) {
    const { data } = await tagsApi.update(id, tagData)
    const idx = tags.value.findIndex((t) => t.id === id)
    if (idx !== -1) tags.value[idx] = data
    return data
  }

  async function deleteTag(id: number) {
    await tagsApi.delete(id)
    tags.value = tags.value.filter((t) => t.id !== id)
  }

  return { tags, loading, fetchTags, createTag, updateTag, deleteTag }
})
