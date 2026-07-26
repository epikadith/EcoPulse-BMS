<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()
const zones = computed(() => store.latestMetrics?.zones || {})
</script>

<template>
  <div class="panel h-full flex flex-col">
    <h3 class="panel-title">Equipment Status</h3>
    <div class="table-container">
      <table v-if="Object.keys(zones).length > 0">
        <thead>
          <tr>
            <th>Zone</th>
            <th>Setpoint (°C)</th>
            <th>Ventilation (%)</th>
            <th>Shading (%)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(data, name) in zones" :key="name">
            <td class="zone-name">{{ name }}</td>
            <td>{{ data.hvac_setpoint?.toFixed(1) }}</td>
            <td>
              <div class="bar-bg">
                <div class="bar-fill" :style="{ width: data.ventilation_rate + '%' }"></div>
              </div>
              <span class="val">{{ data.ventilation_rate?.toFixed(0) }}</span>
            </td>
            <td>
              <div class="bar-bg">
                <div class="bar-fill shade" :style="{ width: data.shading_position + '%' }"></div>
              </div>
              <span class="val">{{ data.shading_position?.toFixed(0) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">Waiting for data...</div>
    </div>
  </div>
</template>

<style scoped>
.panel-title { color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 1rem; }
.table-container { flex: 1; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; text-align: left; }
th { padding: 0.75rem 0.5rem; color: var(--text-secondary); font-size: 0.85rem; font-weight: 500; border-bottom: 1px solid var(--border-glass); }
td { padding: 0.75rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.02); font-variant-numeric: tabular-nums; vertical-align: middle; }
.zone-name { text-transform: capitalize; font-weight: 500; color: var(--accent-cyan); }
.bar-bg { display: inline-block; width: 60px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; margin-right: 8px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent-blue); transition: width 0.3s; }
.bar-fill.shade { background: var(--accent-yellow); }
.val { font-size: 0.85rem; color: var(--text-secondary); }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); min-height: 150px; }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
</style>
