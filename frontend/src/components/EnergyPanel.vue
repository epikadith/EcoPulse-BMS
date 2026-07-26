<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()

const chartOptions = {
  chart: {
    type: 'area',
    animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 1000 } },
    toolbar: { show: false },
    zoom: { enabled: false },
    background: 'transparent',
    fontFamily: 'Outfit, sans-serif'
  },
  colors: ['#3b82f6'],
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
    labels: { style: { colors: '#94a3b8' }, formatter: (val) => val.toFixed(1) },
  },
  grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 4 },
  legend: { labels: { colors: '#94a3b8' } },
  theme: { mode: 'dark' }
}

const series = computed(() => {
  return [
    {
      name: 'Current Energy (kW)',
      data: store.energyHistory.map(pt => [pt.x, pt.y])
    }
  ]
})
</script>

<template>
  <div class="panel h-full flex flex-col">
    <div class="panel-header">
      <h3 class="panel-title">Energy Consumption</h3>
      <div class="stats" v-if="store.latestMetrics">
        <span class="stat-item">
          Total: <strong class="text-gradient">{{ store.latestMetrics.energy.cumulative_kwh.toFixed(1) }} kWh</strong>
        </span>
      </div>
    </div>
    <div class="chart-container">
      <apexchart 
        v-if="store.energyHistory.length > 0"
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
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.panel-title { color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin: 0; }
.stats { font-size: 0.9rem; color: var(--text-secondary); }
.chart-container { flex: 1; min-height: 250px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
</style>
