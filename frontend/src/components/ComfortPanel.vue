<script setup>
import { computed } from 'vue'
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()
const zones = computed(() => store.latestMetrics?.zones || {})

function getComfortStatus(pmv) {
  if (pmv === undefined) return 'unknown'
  const absPmv = Math.abs(pmv)
  if (absPmv < 0.5) return 'comfortable'
  if (absPmv < 1.5) return 'marginal'
  return 'uncomfortable'
}
</script>

<template>
  <div class="panel h-full flex flex-col justify-between">
    <h3 class="panel-title">Thermal Comfort</h3>
    <div class="zones-grid">
      <div v-for="(data, name) in zones" :key="name" class="zone-comfort">
        <div class="zone-name">{{ name }}</div>
        <div class="pmv-value" :class="getComfortStatus(data.pmv)">
          {{ data.pmv?.toFixed(2) }}
        </div>
        <div class="ppd-value">{{ data.ppd?.toFixed(1) }}% PPD</div>
      </div>
      <div v-if="Object.keys(zones).length === 0" class="empty-state">
        Waiting for data...
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-title { margin-bottom: 1rem; color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;}
.zones-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; height: 100%; align-items: center; }
.zone-comfort { display: flex; flex-direction: column; align-items: center; background: rgba(255,255,255,0.03); padding: 1rem 0; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }
.zone-name { font-size: 0.85rem; color: var(--text-secondary); text-transform: capitalize; margin-bottom: 0.5rem; }
.pmv-value { font-size: 1.8rem; font-weight: 700; line-height: 1; margin-bottom: 0.25rem; transition: color 0.3s; }
.ppd-value { font-size: 0.8rem; color: var(--text-secondary); }

.pmv-value.comfortable { color: var(--accent-green); text-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }
.pmv-value.marginal { color: var(--accent-yellow); text-shadow: 0 0 12px rgba(245, 158, 11, 0.4); }
.pmv-value.uncomfortable { color: var(--accent-red); text-shadow: 0 0 12px rgba(239, 68, 68, 0.4); }

.empty-state { grid-column: span 3; text-align: center; color: var(--text-secondary); font-size: 0.9rem; }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.justify-between { justify-content: space-between; }
</style>
