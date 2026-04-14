import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '@/api'
import type { Setting, SettingUpdate } from '@/types'

export const useSettingStore = defineStore('setting', () => {
  const settings = ref<Setting[]>([])
  const loading = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const { data } = await settingsApi.list()
      settings.value = data.settings
    } finally {
      loading.value = false
    }
  }

  async function updateSetting(key: string, value: string) {
    const { data } = await settingsApi.update(key, { value })
    const idx = settings.value.findIndex((s) => s.key === key)
    if (idx !== -1) settings.value[idx] = data
    return data
  }

  async function testApiKey() {
    const { data } = await settingsApi.testApiKey()
    return data
  }

  function getValue(key: string): string {
    const s = settings.value.find((s) => s.key === key)
    return s?.value ?? ''
  }

  return { settings, loading, fetchSettings, updateSetting, testApiKey, getValue }
})
