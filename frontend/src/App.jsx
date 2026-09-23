import { useState, useEffect, useRef, useCallback } from 'react'
import Header from './components/Header'
import DriverMode from './components/DriverMode'
import ControlCenter from './components/ControlCenter'
import AlertBanner from './components/AlertBanner'
import { useSimulation } from './hooks/useSimulation'
import { api } from './services/api'
import './App.css'

const sleep = (ms) => new Promise((res) => setTimeout(res, ms))

export default function App() {
  const [online, setOnline] = useState(true)
  const [network, setNetwork] = useState(null)
  const [missionLocal, setMissionLocal] = useState(null)
  const [optimization, setOptimization] = useState({ status: 'idle', result: null })
  const [convergenceHistory, setConvergenceHistory] = useState([])
  const [oldRoute, setOldRoute] = useState(null)
  const [busy, setBusy] = useState(false)
  const [alert, setAlert] = useState(null)
  const [benchmarkResults, setBenchmarkResults] = useState([])
  const [benchmarkRunning, setBenchmarkRunning] = useState(false)
  const [demoRunning, setDemoRunning] = useState(false)
  const [demoProgress, setDemoProgress] = useState({ pct: 0, label: '' })
  const [mode, setMode] = useState('driver')
  const demoStopRef = useRef(false)

  const sim = useSimulation({ active: true })
  const mission = sim.mission || missionLocal

  const showAlert = useCallback((message, type = 'info', icon) => {
    setAlert({ message, type, icon })
    setTimeout(() => setAlert((a) => (a?.message === message ? null : a)), 5000)
  }, [])

  const loadNetwork = useCallback(async () => {
    try {
      const net = await api.getNetwork()
      setNetwork(net)
      setOnline(true)
    } catch (e) {
      setOnline(false)
      showAlert('Backend unavailable — is the FastAPI server running on :8000?', 'error', '⚠')
    }
  }, [showAlert])

  useEffect(() => {
    loadNetwork()
  }, [loadNetwork])

  // -------------------------------------------------------------- actions
  const handleStart = useCallback(async () => {
    setBusy(true)
    try {
      const m = await api.startEmergency({ severity: 'CRITICAL', pickup: 'A', destination: 'H', ambulance_id: 'AMB-01' })
      setMissionLocal(m)
      setOldRoute(null)
      setOptimization({ status: 'running', result: null })
      const opt = await api.optimize(m.mission_id, 'QPSO')
      setOptimization({ status: 'done', result: opt.optimization })
      setConvergenceHistory(opt.optimization.convergence_history || [])
      setMissionLocal(opt.mission)
      showAlert('Emergency created — QPSO route optimized, green corridor active.', 'success', '🚨')
    } catch (e) {
      showAlert(e.message || 'Failed to start emergency', 'error', '⚠')
    } finally {
      setBusy(false)
    }
  }, [showAlert])

  const handleInjectIncident = useCallback(async (missionId) => {
    const mid = missionId || mission?.mission_id
    if (!mid) return
    setBusy(true)
    try {
      setOldRoute(mission?.route || null)
      const res = await api.injectIncident(mid)
      showAlert(`⚠ Incident on ${res.incident.road_name} — route disrupted, re-optimizing…`, 'warning', '⚠')
      await sleep(600)
      setOptimization((o) => ({ ...o, status: 'running' }))
      const reopt = await api.reoptimize(mid, 'QPSO')
      setOptimization({ status: 'done', result: reopt.optimization })
      setConvergenceHistory(reopt.optimization.convergence_history || [])
      setMissionLocal(reopt.mission)
      showAlert('New route found — green corridor updated.', 'success', '🟢')
    } catch (e) {
      showAlert(e.message || 'Incident handling failed', 'error', '⚠')
    } finally {
      setBusy(false)
    }
  }, [mission, showAlert])

  const handleReoptimize = useCallback(async (missionId) => {
    const mid = missionId || mission?.mission_id
    if (!mid) return
    setBusy(true)
    try {
      setOldRoute(mission?.route || null)
      setOptimization((o) => ({ ...o, status: 'running' }))
      const reopt = await api.reoptimize(mid, 'QPSO')
      setOptimization({ status: 'done', result: reopt.optimization })
      setConvergenceHistory(reopt.optimization.convergence_history || [])
      setMissionLocal(reopt.mission)
      showAlert('Route re-optimized.', 'success', '🔄')
    } catch (e) {
      showAlert(e.message || 'Re-optimization failed', 'error', '⚠')
    } finally {
      setBusy(false)
    }
  }, [mission, showAlert])

  const handleReset = useCallback(async () => {
    setBusy(true)
    demoStopRef.current = true
    setDemoRunning(false)
    try {
      await api.reset()
      setMissionLocal(null)
      setOptimization({ status: 'idle', result: null })
      setConvergenceHistory([])
      setOldRoute(null)
      setBenchmarkResults([])
      await loadNetwork()
      showAlert('Simulation reset.', 'info', '🔁')
    } catch (e) {
      showAlert(e.message || 'Reset failed', 'error', '⚠')
    } finally {
      setBusy(false)
    }
  }, [loadNetwork, showAlert])

  const handleRunBenchmark = useCallback(async () => {
    setBenchmarkRunning(true)
    try {
      const res = await api.runBenchmark({ source: 'A', destination: 'H', algorithms: ['DIJKSTRA', 'ASTAR', 'QPSO', 'PSO', 'GA'] })
      setBenchmarkResults(res.results)
    } catch (e) {
      showAlert(e.message || 'Benchmark failed', 'error', '⚠')
    } finally {
      setBenchmarkRunning(false)
    }
  }, [showAlert])

  // ---------------------------------------------------------- full demo
  const waitForArrival = async (maxWaitMs = 60000) => {
    const start = Date.now()
    while (Date.now() - start < maxWaitMs) {
      if (demoStopRef.current) return false
      const amb = await api.getAmbulance().catch(() => null)
      if (amb?.status === 'ARRIVED') return true
      await sleep(500)
    }
    return false
  }

  const runFullDemo = useCallback(async () => {
    demoStopRef.current = false
    setDemoRunning(true)
    try {
      setDemoProgress({ pct: 5, label: 'Resetting simulation…' })
      await api.reset()
      await loadNetwork()
      setMissionLocal(null)
      setOptimization({ status: 'idle', result: null })
      setConvergenceHistory([])
      setOldRoute(null)
      await sleep(400)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 15, label: 'Creating critical emergency…' })
      const m = await api.startEmergency({ severity: 'CRITICAL', pickup: 'A', destination: 'H', ambulance_id: 'AMB-01' })
      setMissionLocal(m)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 30, label: 'Running QPSO optimization…' })
      setOptimization({ status: 'running', result: null })
      const opt = await api.optimize(m.mission_id, 'QPSO')
      setOptimization({ status: 'done', result: opt.optimization })
      setConvergenceHistory(opt.optimization.convergence_history || [])
      setMissionLocal(opt.mission)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 45, label: 'Green corridor active — ambulance en route…' })
      await sleep(4000)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 60, label: 'Injecting traffic incident…' })
      setOldRoute(opt.mission.route)
      const inc = await api.injectIncident(m.mission_id)
      showAlert(`⚠ Incident on ${inc.incident.road_name} — route disrupted`, 'warning', '⚠')
      await sleep(1200)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 75, label: 'Re-optimizing route with QPSO…' })
      setOptimization((o) => ({ ...o, status: 'running' }))
      const reopt = await api.reoptimize(m.mission_id, 'QPSO')
      setOptimization({ status: 'done', result: reopt.optimization })
      setConvergenceHistory(reopt.optimization.convergence_history || [])
      setMissionLocal(reopt.mission)
      showAlert('New route found — green corridor regenerated.', 'success', '🟢')
      if (demoStopRef.current) return

      setDemoProgress({ pct: 85, label: 'Ambulance continuing to hospital…' })
      const arrived = await waitForArrival(60000)
      if (demoStopRef.current) return

      setDemoProgress({ pct: 100, label: arrived ? '🏥 Hospital reached — mission complete!' : 'Demo timeline finished.' })
      showAlert(arrived ? 'Mission complete — hospital reached.' : 'Demo sequence finished.', 'success', '🏥')
    } catch (e) {
      showAlert(e.message || 'Demo run failed', 'error', '⚠')
    } finally {
      await sleep(1500)
      setDemoRunning(false)
    }
  }, [loadNetwork, showAlert])

  const stopDemo = useCallback(() => {
    demoStopRef.current = true
    setDemoRunning(false)
    setDemoProgress({ pct: 0, label: '' })
  }, [])

  // Driver Mode's single "deactivate emergency" control -- ends the
  // mission and returns every simulated signal to NORMAL via a full
  // simulation reset, matching "Return the signal to NORMAL after the
  // ambulance passes" / mission teardown semantics for the demo.
  const handleDeactivate = useCallback(async () => {
    await handleReset()
    showAlert('Emergency deactivated — signals returned to NORMAL.', 'info', '⚪')
  }, [handleReset, showAlert])

  return (
    <div className="qgc-app">
      <Header online={online} missionStatus={mission?.status} mode={mode} onModeChange={setMode} />
      <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />

      {mode === 'driver' ? (
        <DriverMode
          network={network}
          mission={mission}
          ambulance={sim.ambulance}
          signals={sim.signals}
          navigation={sim.navigation}
          busy={busy}
          onActivate={handleStart}
          onDeactivate={handleDeactivate}
        />
      ) : (
        <ControlCenter
          network={network}
          mission={mission}
          sim={sim}
          oldRoute={oldRoute}
          optimization={optimization}
          convergenceHistory={convergenceHistory}
          benchmarkResults={benchmarkResults}
          benchmarkRunning={benchmarkRunning}
          busy={busy}
          demoRunning={demoRunning}
          demoProgress={demoProgress}
          onStart={handleStart}
          onInjectIncident={handleInjectIncident}
          onReoptimize={handleReoptimize}
          onReset={handleReset}
          onRunDemo={runFullDemo}
          onStopDemo={stopDemo}
          onRunBenchmark={handleRunBenchmark}
        />
      )}
    </div>
  )
}
