const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (_) {}
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const api = {
  health: () => req('/health'),
  getNetwork: () => req('/network'),
  getConfig: () => req('/config'),
  updateConfig: (patch) => req('/config', { method: 'POST', body: JSON.stringify(patch) }),

  startEmergency: (payload) => req('/emergency/start', { method: 'POST', body: JSON.stringify(payload) }),
  optimize: (missionId, algorithm = 'QPSO') =>
    req('/optimize', { method: 'POST', body: JSON.stringify({ mission_id: missionId, algorithm }) }),
  reoptimize: (missionId, algorithm = 'QPSO') =>
    req('/reoptimize', { method: 'POST', body: JSON.stringify({ mission_id: missionId, algorithm }) }),
  injectIncident: (missionId, edgeId = null) =>
    req('/traffic/incident', { method: 'POST', body: JSON.stringify({ mission_id: missionId, edge_id: edgeId }) }),

  getAmbulance: () => req('/ambulance'),
  getSignals: () => req('/signals'),
  getState: () => req('/state'),
  getTimeline: () => req('/timeline'),
  getConvergence: (missionId) => req(`/convergence/${missionId}`),

  activateCorridor: (missionId) => req('/corridor/activate', { method: 'POST', body: JSON.stringify({ mission_id: missionId }) }),
  deactivateCorridor: (missionId) => req('/corridor/deactivate', { method: 'POST', body: JSON.stringify({ mission_id: missionId }) }),

  runBenchmark: (payload) => req('/benchmark', { method: 'POST', body: JSON.stringify(payload) }),
  getBenchmarkResults: () => req('/benchmark/results'),

  getNavigation: (missionId) => req(`/navigation/${missionId}`),
  getCommandLog: () => req('/control/commands'),
  issueSignalCommand: (signalId, command, reason) =>
    req(`/signals/${signalId}/priority`, { method: 'POST', body: JSON.stringify({ command, reason }) }),

  reset: () => req('/reset', { method: 'POST' }),
}
