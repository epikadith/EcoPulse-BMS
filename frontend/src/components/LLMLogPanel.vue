<script setup>
import { useMetricsStore } from '../stores/metrics'

const store = useMetricsStore()
</script>

<template>
  <div class="panel h-full flex flex-col">
    <h3 class="panel-title">Agent Reasoning Log</h3>
    <div class="logs-container">
      <div v-if="store.agentLogs.length === 0" class="empty-state">
        Waiting for agent actions...
      </div>
      <div v-for="(log, idx) in store.agentLogs" :key="idx" class="log-entry">
        <div class="log-header">
          <span class="timestamp">{{ log.timestamp }}</span>
          <span class="status" :class="{ error: !log.data.success }">
            {{ log.data.success ? 'Success' : 'Failed' }}
          </span>
        </div>
        <div v-if="log.data.error" class="error-msg">{{ log.data.error }}</div>
        <div v-if="log.data.reasoning" class="reasoning">
          <span class="reasoning-label">Reasoning:</span> {{ log.data.reasoning }}
        </div>
        <div v-if="log.data.actions_executed" class="actions">
          <div v-for="(act, aIdx) in log.data.actions_executed" :key="aIdx" class="action">
            <span class="tool-name">{{ act.tool }}</span>
            <span class="args">{{ JSON.stringify(act.args) }}</span>
          </div>
          <div v-if="log.data.actions_executed.length === 0" class="no-actions">
            No actions taken this cycle.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-title { color: var(--text-secondary); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 1rem; }
.logs-container { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; padding-right: 0.5rem; max-height: 250px; }
.log-entry { background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 0.75rem; font-size: 0.85rem; }
.log-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.timestamp { color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.status { color: var(--accent-green); font-weight: 500; }
.status.error { color: var(--accent-red); }
.error-msg { color: var(--accent-red); margin-bottom: 0.5rem; }
.reasoning { color: var(--text-secondary); margin-bottom: 0.5rem; line-height: 1.4; font-size: 0.85rem; background: rgba(6, 182, 212, 0.05); padding: 0.5rem; border-radius: 6px; border-left: 3px solid var(--accent-cyan); }
.reasoning-label { color: var(--accent-cyan); font-weight: 600; }
.action { display: flex; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.25rem; font-family: monospace; }
.tool-name { color: var(--accent-cyan); font-weight: bold; }
.args { color: var(--text-secondary); word-break: break-all; }
.no-actions { color: var(--text-secondary); font-style: italic; }
.empty-state { text-align: center; color: var(--text-secondary); margin-top: 2rem; }
.h-full { height: 100%; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
</style>
