<template>
  <div>
    <n-space justify="space-between" align="center" style="margin-bottom: 16px">
      <n-h2 style="margin: 0">标签管理</n-h2>
      <n-space>
        <n-switch v-model:value="showInactive" @update:value="tagStore.fetchTags(!showInactive)">
          <template #checked>显示全部</template>
          <template #unchecked>仅活跃</template>
        </n-switch>
        <n-button type="primary" @click="openCreateModal">添加标签</n-button>
        <n-button @click="tagStore.fetchTags(!showInactive)">刷新</n-button>
      </n-space>
    </n-space>

    <n-spin :show="tagStore.loading">
      <n-empty v-if="tagStore.tags.length === 0 && !tagStore.loading" description="暂无标签">
        <template #extra>
          <n-button size="small" @click="openCreateModal">添加第一个标签</n-button>
        </template>
      </n-empty>

      <n-grid v-else :cols="2" :x-gap="16" :y-gap="12">
        <n-gi v-for="tag in tagStore.tags" :key="tag.id">
          <n-card size="small" hoverable>
            <template #header>
              <n-space align="center">
                <n-text strong>{{ tag.name }}</n-text>
                <n-tag size="small" round>{{ tag.value }}</n-tag>
                <n-tag v-if="tag.is_system" type="warning" size="small" round>系统</n-tag>
                <n-tag v-if="!tag.is_active" type="error" size="small" round>已停用</n-tag>
              </n-space>
            </template>
            <template #header-extra>
              <n-space size="small">
                <n-button v-if="tag.is_active" size="tiny" type="warning" quaternary @click="handleToggleActive(tag)">停用</n-button>
                <n-button v-else size="tiny" type="success" quaternary @click="handleToggleActive(tag)">启用</n-button>
                <n-button size="tiny" quaternary @click="openEditModal(tag)">编辑</n-button>
                <n-popconfirm v-if="!tag.is_system" @positive-click="handleDelete(tag.id)">
                  <template #trigger>
                    <n-button size="tiny" type="error" quaternary>删除</n-button>
                  </template>
                  确定删除标签「{{ tag.name }}」？
                </n-popconfirm>
              </n-space>
            </template>
            <n-text depth="3">{{ tag.description ?? '无描述' }}</n-text>
            <template #footer>
              <n-text depth="3" style="font-size: 12px">更新于 {{ formatTime(tag.updated_at) }}</n-text>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>

    <n-modal
      v-model:show="showModal"
      preset="card"
      :title="isEditing ? '编辑标签' : '添加标签'"
      style="width: 500px"
      :mask-closable="false"
    >
      <n-form ref="formRef" :model="formModel" :rules="formRules" label-placement="left" label-width="80">
        <n-form-item label="标签名称" path="name">
          <n-input v-model:value="formModel.name" placeholder="如：非法入侵" />
        </n-form-item>
        <n-form-item v-if="!isEditing" label="标签值" path="value">
          <n-input v-model:value="formModel.value" placeholder="如：illegal_intrusion（英文标识）" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="formModel.description" type="textarea" placeholder="标签描述（可选）" :rows="3" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">{{ isEditing ? '保存' : '创建' }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { useMessage } from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { useTagStore } from '@/stores/tag'
import type { Tag, TagCreate, TagUpdate } from '@/types'

const message = useMessage()
const tagStore = useTagStore()

const showInactive = ref(false)
const showModal = ref(false)
const isEditing = ref(false)
const submitting = ref(false)
const editingTagId = ref<number | null>(null)
const formRef = ref<FormInst | null>(null)

const formModel = reactive({
  name: '',
  value: '',
  description: '',
})

const formRules: FormRules = {
  name: { required: true, message: '请输入标签名称', trigger: 'blur' },
  value: { required: true, message: '请输入标签值', trigger: 'blur' },
}

function formatTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function openCreateModal() {
  isEditing.value = false
  editingTagId.value = null
  formModel.name = ''
  formModel.value = ''
  formModel.description = ''
  showModal.value = true
}

function openEditModal(tag: Tag) {
  isEditing.value = true
  editingTagId.value = tag.id
  formModel.name = tag.name
  formModel.value = tag.value
  formModel.description = tag.description ?? ''
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (isEditing.value && editingTagId.value) {
      const updateData: TagUpdate = { name: formModel.name }
      if (formModel.description) updateData.description = formModel.description
      await tagStore.updateTag(editingTagId.value, updateData)
      message.success('标签已更新')
    } else {
      const createData: TagCreate = {
        name: formModel.name,
        value: formModel.value,
      }
      if (formModel.description) createData.description = formModel.description
      await tagStore.createTag(createData)
      message.success('标签已创建')
    }
    showModal.value = false
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleToggleActive(tag: Tag) {
  try {
    await tagStore.updateTag(tag.id, { is_active: !tag.is_active })
    message.success(tag.is_active ? '标签已停用' : '标签已启用')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '操作失败')
  }
}

async function handleDelete(id: number) {
  try {
    await tagStore.deleteTag(id)
    message.success('标签已删除')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? '删除失败')
  }
}

onMounted(() => {
  tagStore.fetchTags(true)
})
</script>
