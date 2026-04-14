<template>
  <div>
    <n-h2 style="margin-bottom: 16px">设置</n-h2>

    <n-spin :show="settingStore.loading">
      <n-grid :cols="1" :y-gap="16">
        <n-gi>
          <n-card title="API 配置">
            <n-form label-placement="left" label-width="120" :show-feedback="false">
              <n-form-item label="API Key">
                <n-input
                  v-model:value="apiKeyValue"
                  type="password"
                  show-password-on="click"
                  placeholder="输入视频分析 API Key"
                  style="width: 400px"
                />
                <n-button type="primary" style="margin-left: 12px" :loading="savingApiKey" @click="handleSaveApiKey">
                  保存
                </n-button>
                <n-button style="margin-left: 8px" :loading="testingApiKey" @click="handleTestApiKey">
                  测试连接
                </n-button>
              </n-form-item>
              <n-form-item label="MCP 模式">
                <n-select
                  v-model:value="mcpMode"
                  :options="mcpModeOptions"
                  style="width: 200px"
                  @update:value="handleSaveMcpMode"
                />
              </n-form-item>
            </n-form>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="处理配置">
            <n-form label-placement="left" label-width="120" :show-feedback="false">
              <n-form-item label="最大并发数">
                <n-input-number
                  v-model:value="maxWorkers"
                  :min="1"
                  :max="10"
                  style="width: 200px"
                />
                <n-button type="primary" style="margin-left: 12px" @click="handleSaveMaxWorkers">
                  保存
                </n-button>
              </n-form-item>
            </n-form>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="系统信息">
            <n-descriptions :column="1" bordered label-placement="left">
              <n-descriptions-item label="应用名称">Video Auto Annotation</n-descriptions-item>
              <n-descriptions-item label="版本">1.0.0</n-descriptions-item>
              <n-descriptions-item label="后端状态">
                <n-tag :type="backendOnline ? 'success' : 'error'" size="small" round>
                  {{ backendOnline ? '在线' : '离线' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="API 文档">
                <n-a href="/docs" target="_blank">/docs</n-a>
              </n-descriptions-item>
            </n-descriptions>
          </n-card>
        </n-gi>

        <n-gi>
          <n-card title="危险操作">
            <n-space>
              <n-popconfirm @positive-click="handleResetDatabase">
                <template #trigger>
                  <n-button type="error">重置数据库</n-button>
                </template>
                确定重置数据库？这将删除所有任务、标注和自定义标签数据，此操作不可恢复！
              </n-popconfirm>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { useSettingStore } from '@/stores/setting'
import { healthApi } from '@/api'

const message = useMessage()
const dialog = useDialog()
const settingStore = useSettingStore()

const apiKeyValue = ref('')
const mcpMode = ref('ZHIPU')
const maxWorkers = ref(5)
const savingApiKey = ref(false)
const testingApiKey = ref(false)
const backendOnline = ref(false)

const mcpModeOptions = [
  { label: '智谱 (ZHIPU)', value: 'ZHIPU' },
  { label: 'OpenAI', value: 'OPENAI' },
  { label: '自定义', value: 'CUSTOM' },
]

async function handleSaveApiKey() {
  if (!apiKeyValue.value.trim()) {
    message.warning('请输入 API Key')
    return
  }
  savingApiKey.value = true
  try {
    await settingStore.updateSetting('api_key', apiKeyValue.value)
    message.success('API Key 已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '保存失败')
  } finally {
    savingApiKey.value = false
  }
}

async function handleTestApiKey() {
  if (!apiKeyValue.value.trim()) {
    message.warning('请先输入并保存 API Key')
    return
  }
  testingApiKey.value = true
  try {
    await settingStore.updateSetting('api_key', apiKeyValue.value)
    const result = await settingStore.testApiKey()
    if (result.success) {
      message.success('API 连接测试成功')
    } else {
      message.error('API 连接测试失败: ' + (result.message ?? '未知错误'))
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '测试失败')
  } finally {
    testingApiKey.value = false
  }
}

async function handleSaveMcpMode(value: string) {
  try {
    await settingStore.updateSetting('mcp_mode', value)
    message.success('MCP 模式已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '保存失败')
  }
}

async function handleSaveMaxWorkers() {
  try {
    await settingStore.updateSetting('max_workers', String(maxWorkers.value))
    message.success('并发数已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '保存失败')
  }
}

function handleResetDatabase() {
  message.warning('数据库重置功能暂未实现，请手动删除数据库文件后重启应用')
}

onMounted(async () => {
  await settingStore.fetchSettings()

  const apiKey = settingStore.getValue('api_key')
  if (apiKey) apiKeyValue.value = '••••••••'

  const mode = settingStore.getValue('mcp_mode')
  if (mode) mcpMode.value = mode

  const workers = settingStore.getValue('max_workers')
  if (workers) maxWorkers.value = parseInt(workers, 10) || 5

  try {
    await healthApi.check()
    backendOnline.value = true
  } catch {
    backendOnline.value = false
  }
})
</script>
