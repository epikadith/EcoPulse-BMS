<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()
const weather = computed(() => store.latestMetrics?.outdoor || { temperature: 0, humidity: 0, solar_irradiance: 0 })
const simTime = computed(() => {
  if (!store.latestMetrics) return '00:00'
  const m = store.latestMetrics.timestamp_minutes
  const hours = Math.floor(m / 60) % 24
  const mins = Math.floor(m % 60)
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
})
</script>

<template>
  <div class="panel h-full flex flex-col justify-between">
    <h3 class="panel-title">Environment & Time</h3>
    <div class="metrics-grid">
      <div class="metric">
        <div class="label">Sim Time</div>
        <div class="value">{{ simTime }}</div>
        <div class="sub-label">Day {{ store.latestMetrics?.day || 0 }}</div>
      </div>
      <div class="metric">
        <div class="label">Outdoor Temp</div>
        <div class="value">{{ weather.temperature.toFixed(1) }}<span class="unit">°C</span></div>
      </div>
      <div class="metric">
        <div class="label">Humidity</div>
        <div class="value">{{ weather.humidity.toFixed(0) }}<span class="unit">%RH</span></div>
      </div>
      <div class="metric">
        <div class="label">Solar Irradiance</div>
        <div class="value">{{ Math.round(weather.solar_irradiance) }}<span class="unit">W/m²</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-title { margin-bottom: 1rem; color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;}
.metrics-grid { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem; }
.metric { display: flex; flex-direction: column; }
.label { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem; }
.value { font-size: 2rem; font-weight: 600; color: var(--text-primary); line-height: 1; }
.unit { font-size: 1rem; font-weight: 400; color: var(--text-secondary); margin-left: 0.25rem; }
.sub-label { font-size: 0.8rem; color: var(--accent-cyan); font-weight: 500; margin-top: 0.25rem; }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.justify-between { justify-content: space-between; }
</style>
