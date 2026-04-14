<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-notification-provider>
      <n-message-provider>
        <n-dialog-provider>
          <n-layout has-sider style="height: 100vh">
            <n-layout-sider
              bordered
              :width="220"
              :collapsed-width="64"
              collapse-mode="width"
              :collapsed="collapsed"
              show-trigger
              @collapse="collapsed = true"
              @expand="collapsed = false"
            >
              <div class="logo" :class="{ 'logo-collapsed': collapsed }">
                <n-text v-if="!collapsed" strong style="font-size: 18px">Video Annotation</n-text>
                <n-text v-else strong style="font-size: 16px">VA</n-text>
              </div>
              <n-menu
                :options="menuOptions"
                :value="activeKey"
                :collapsed="collapsed"
                :collapsed-width="64"
                :collapsed-icon-size="22"
                @update:value="handleMenuUpdate"
              />
            </n-layout-sider>
            <n-layout>
              <n-layout-header bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between;">
                <n-breadcrumb>
                  <n-breadcrumb-item @click="router.push('/')">首页</n-breadcrumb-item>
                  <n-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
                    <span v-if="item.current">{{ item.label }}</span>
                    <a v-else style="cursor: pointer" @click="router.push(item.path)">{{ item.label }}</a>
                  </n-breadcrumb-item>
                </n-breadcrumb>
                <n-space align="center">
                  <n-tag :type="backendOnline ? 'success' : 'error'" size="small" round>
                    {{ backendOnline ? '后端已连接' : '后端未连接' }}
                  </n-tag>
                </n-space>
              </n-layout-header>
              <n-layout-content
                content-style="padding: 24px; overflow: auto;"
                :native-scrollbar="false"
              >
                <router-view />
              </n-layout-content>
            </n-layout>
          </n-layout>
        </n-dialog-provider>
      </n-message-provider>
    </n-notification-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { darkTheme, NIcon, zhCN, dateZhCN } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  VideocamOutline,
  PricetagsOutline,
  SettingsOutline,
  DocumentTextOutline,
} from '@vicons/ionicons5'
import { healthApi } from '@/api'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const backendOnline = ref(false)

onMounted(async () => {
  try {
    await healthApi.check()
    backendOnline.value = true
  } catch {
    backendOnline.value = false
  }
  setInterval(async () => {
    try {
      await healthApi.check()
      backendOnline.value = true
    } catch {
      backendOnline.value = false
    }
  }, 30000)
})

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/tasks')) return 'tasks'
  if (path.startsWith('/annotations')) return 'annotations'
  if (path.startsWith('/tags')) return 'tags'
  if (path.startsWith('/settings')) return 'settings'
  return 'tasks'
})

const routeLabelMap: Record<string, string> = {
  Tasks: '任务管理',
  TaskDetail: '任务详情',
  Annotations: '标注预览',
  Tags: '标签管理',
  Settings: '设置',
}

const breadcrumbs = computed(() => {
  const items: { label: string; path: string; current: boolean }[] = []

  if (route.name === 'TaskDetail') {
    items.push({ label: '任务管理', path: '/tasks', current: false })
    items.push({ label: '任务详情', path: route.path, current: true })
  } else {
    const label = routeLabelMap[route.name as string] ?? '未知'
    items.push({ label, path: route.path, current: true })
  }

  return items
})

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  {
    label: '任务管理',
    key: 'tasks',
    icon: renderIcon(VideocamOutline),
  },
  {
    label: '标注预览',
    key: 'annotations',
    icon: renderIcon(DocumentTextOutline),
  },
  {
    label: '标签管理',
    key: 'tags',
    icon: renderIcon(PricetagsOutline),
  },
  {
    label: '设置',
    key: 'settings',
    icon: renderIcon(SettingsOutline),
  },
]

function handleMenuUpdate(key: string) {
  router.push({ name: key.charAt(0).toUpperCase() + key.slice(1) })
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--n-border-color);
  transition: all 0.3s;
}

.logo-collapsed {
  font-size: 14px;
}
</style>
