import { defineStore } from 'pinia'

export const useMetricsStore = defineStore('metrics', {
  state: () => ({
    latestMetrics: null,
    energyHistory: [],  // Time-series data for energy consumption
    carbonHistory: [],  // Time-series data for carbon emissions
    agentLogs: [],      // Array of reasoning actions
    maxHistory: 100,    // Limit to prevent memory bloat
    agentStatus: 'idle' // 'idle' or 'thinking'
  }),
  actions: {
    setAgentStatus(status) {
      this.agentStatus = status
    },
    updateMetrics(metrics) {
      this.latestMetrics = metrics
      
      const now = Date.now()

      // Update energy history for charts
      this.energyHistory.push({
        x: now,
        y: metrics.energy.current_kw,
        baseline: metrics.energy.baseline_kwh
      })

      // Update carbon history for charts
      this.carbonHistory.push({
        x: now,
        y: metrics.carbon.current_kg_per_h
      })

      // Trim histories
      if (this.energyHistory.length > this.maxHistory) {
        this.energyHistory.shift()
      }
      if (this.carbonHistory.length > this.maxHistory) {
        this.carbonHistory.shift()
      }
    },
    addAgentLog(log) {
      this.agentLogs.unshift({
        timestamp: new Date().toLocaleTimeString(),
        data: log
      })
      if (this.agentLogs.length > 50) {
        this.agentLogs.pop()
      }
    }
  }
})
