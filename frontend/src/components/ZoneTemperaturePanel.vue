<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()

const chartOptions = {
  chart: {
    type: 'bar',
    toolbar: { show: false },
    background: 'transparent',
    fontFamily: 'Outfit, sans-serif',
    animations: { enabled: true }
  },
  plotOptions: {
    bar: { horizontal: false, columnWidth: '55%', borderRadius: 4, dataLabels: { position: 'top' } }
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val.toFixed(1) + '°C',
    offsetY: -20,
    style: { fontSize: '12px', colors: ['#f8fafc'] }
  },
  colors: ['#06b6d4', '#3b82f6'], 
  xaxis: {
    categories: ['Space 1', 'Space 2', 'Space 3', 'Space 4', 'Space 5'],
    labels: { style: { colors: '#94a3b8' }, textTransform: 'capitalize' },
    axisBorder: { show: false },
    axisTicks: { show: false }
  },
  yaxis: {
    labels: { style: { colors: '#94a3b8' } },
    min: 15, max: 30
  },
  grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 4 },
  legend: { labels: { colors: '#94a3b8' }, position: 'top' },
  theme: { mode: 'dark' }
}

const series = computed(() => {
  const z = store.latestMetrics?.zones
  if (!z || Object.keys(z).length === 0) return []
  return [
    {
      name: 'Current Temp',
      data: [z['space1-1']?.indoor_temp || 0, z['space2-1']?.indoor_temp || 0, z['space3-1']?.indoor_temp || 0, z['space4-1']?.indoor_temp || 0, z['space5-1']?.indoor_temp || 0]
    },
    {
      name: 'Setpoint',
      data: [z['space1-1']?.hvac_setpoint || 0, z['space2-1']?.hvac_setpoint || 0, z['space3-1']?.hvac_setpoint || 0, z['space4-1']?.hvac_setpoint || 0, z['space5-1']?.hvac_setpoint || 0]
    }
  ]
})
</script>

<template>
  <div class="panel h-full flex flex-col">
    <h3 class="panel-title">Zone Temperatures</h3>
    <div class="chart-container">
      <apexchart 
        v-if="series.length > 0"
        type="bar" 
        height="100%" 
        :options="chartOptions" 
        :series="series" 
      />
      <div v-else class="empty-state">Waiting for data...</div>
    </div>
  </div>
</template>

<style scoped>
.panel-title { color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 1rem; }
.chart-container { flex: 1; min-height: 250px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
</style>
