import { ref, onMounted, onUnmounted } from 'vue'
import { useMetricsStore } from '../stores/metrics'

export function useWebSocket(url = 'ws://localhost:8765') {
  const ws = ref(null)
  const isConnected = ref(false)
  const store = useMetricsStore()

  const connect = () => {
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      console.log('WebSocket Connected')
      isConnected.value = true
    }

    ws.value.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        
        if (message.type === 'metrics') {
          store.updateMetrics(message.data)
        } else if (message.type === 'agent_action') {
          store.addAgentLog(message.data)
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }

    ws.value.onclose = () => {
      console.log('WebSocket Disconnected')
      isConnected.value = false
      // Attempt reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket Error:', error)
      ws.value.close()
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    if (ws.value) {
      ws.value.close()
    }
  })

  return {
    isConnected,
    ws
  }
}
