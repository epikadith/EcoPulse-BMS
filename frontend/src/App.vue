<script setup>
import { useWebSocket } from './composables/useWebSocket'
import EnergyPanel from './components/EnergyPanel.vue'
import ComfortPanel from './components/ComfortPanel.vue'
import ZoneTemperaturePanel from './components/ZoneTemperaturePanel.vue'
import WeatherPanel from './components/WeatherPanel.vue'
import CarbonPanel from './components/CarbonPanel.vue'
import HVACStatusPanel from './components/HVACStatusPanel.vue'
import LLMLogPanel from './components/LLMLogPanel.vue'

// Initialize WebSocket connection on app mount
const { isConnected } = useWebSocket()
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div>
        <h1 class="text-gradient">EcoPulse</h1>
        <p class="subtitle">Intelligent Building Management System</p>
      </div>
      <div class="connection-status">
        <div class="status-indicator" :class="{ connected: isConnected }"></div>
        <span>{{ isConnected ? 'Live' : 'Connecting...' }}</span>
      </div>
    </header>

    <main class="dashboard-grid">
      <!-- Top Row: Weather and High-level stats -->
      <div class="grid-col-span-4">
        <WeatherPanel />
      </div>
      <div class="grid-col-span-4">
        <CarbonPanel />
      </div>
      <div class="grid-col-span-4">
        <ComfortPanel />
      </div>

      <!-- Middle Row: Charts and Core Data -->
      <div class="grid-col-span-8">
        <EnergyPanel />
      </div>
      <div class="grid-col-span-4">
        <ZoneTemperaturePanel />
      </div>

      <!-- Bottom Row: Logs and granular status -->
      <div class="grid-col-span-6">
        <HVACStatusPanel />
      </div>
      <div class="grid-col-span-6">
        <LLMLogPanel />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 3rem;
  border-bottom: 1px solid var(--border-glass);
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  border: 1px solid var(--border-glass);
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--accent-red);
  box-shadow: 0 0 10px var(--accent-red);
  transition: all 0.3s ease;
}

.status-indicator.connected {
  background-color: var(--accent-green);
  box-shadow: 0 0 10px var(--accent-green);
}

/* Grid span helpers */
.grid-col-span-4 { grid-column: span 4; }
.grid-col-span-6 { grid-column: span 6; }
.grid-col-span-8 { grid-column: span 8; }

@media (max-width: 1024px) {
  .grid-col-span-4, .grid-col-span-6, .grid-col-span-8 {
    grid-column: span 12;
  }
}
</style>
