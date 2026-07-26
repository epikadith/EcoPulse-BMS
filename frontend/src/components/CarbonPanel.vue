<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()
const carbon = computed(() => store.latestMetrics?.carbon || { current_kg_per_h: 0, cumulative_kg: 0 })

const chartOptions = {
  chart: {
    type: 'area',
    animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 1000 } },
    toolbar: { show: false },
    zoom: { enabled: false },
    background: 'transparent',
    fontFamily: 'Outfit, sans-serif',
    sparkline: { enabled: false }
  },
  colors: ['#10b981'],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05, stops: [0, 100] }
  },
  xaxis: {
    type: 'datetime',
    labels: { style: { colors: '#94a3b8' } },
    axisBorder: { show: false },
    axisTicks: { show: false }
  },
  yaxis: {
    labels: { style: { colors: '#94a3b8' }, formatter: (val) => val.toFixed(2) },
  },
  grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 4 },
  legend: { show: false },
  theme: { mode: 'dark' }
}

const series = computed(() => {
  return [
    {
      name: 'CO₂ Rate (kg/h)',
      data: store.carbonHistory.map(pt => [pt.x, pt.y])
    }
  ]
})
</script>

<template>
  <div class="panel h-full flex flex-col">
    <div class="panel-header">
      <h3 class="panel-title">Carbon Footprint</h3>
      <div class="stats">
        <span class="stat-item">
          Total: <strong class="text-gradient">{{ carbon.cumulative_kg.toFixed(1) }} kg CO₂</strong>
        </span>
      </div>
    </div>
    <div class="metrics-row">
      <div class="metric">
        <div class="label">Emission Rate</div>
        <div class="value">{{ carbon.current_kg_per_h.toFixed(2) }}<span class="unit">kg/h</span></div>
      </div>
    </div>
    <div class="chart-container">
      <apexchart 
        v-if="store.carbonHistory.length > 0"
        type="area" 
        height="100%" 
        :options="chartOptions" 
        :series="series" 
      />
      <div v-else class="empty-state">Waiting for data...</div>
    </div>
  </div>
</template>

<style scoped>
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.panel-title { color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin: 0; }
.stats { font-size: 0.9rem; color: var(--text-secondary); }
.metrics-row { display: flex; gap: 1.5rem; margin-bottom: 0.75rem; }
.metric { display: flex; flex-direction: column; }
.label { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.15rem; }
.value { font-size: 1.5rem; font-weight: 600; color: var(--text-primary); line-height: 1; }
.unit { font-size: 0.85rem; font-weight: 400; color: var(--text-secondary); margin-left: 0.25rem; }
.chart-container { flex: 1; min-height: 150px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
</style>
