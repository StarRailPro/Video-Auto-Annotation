import { ref, onUnmounted, watch } from 'vue'
import type { WsProgressData } from '@/types'

export function useWebSocket(taskId: number) {
  const connected = ref(false)
  const lastData = ref<WsProgressData | null>(null)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 10
  let stopped = false

  function connect() {
    if (stopped) return

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/ws/progress/${taskId}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return
      try {
        lastData.value = JSON.parse(event.data)
      } catch {
        // ignore non-json
      }
    }

    ws.onclose = () => {
      connected.value = false
      if (!stopped && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        const delay = Math.min(3000 * reconnectAttempts, 15000)
        reconnectTimer = setTimeout(() => connect(), delay)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }

    const pingInterval = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    onUnmounted(() => {
      clearInterval(pingInterval)
      stop()
    })
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
    connected.value = false
  }

  function stop() {
    stopped = true
    disconnect()
  }

  return { connected, lastData, connect, disconnect, stop }
}
