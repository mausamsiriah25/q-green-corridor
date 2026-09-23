const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

export default function EmergencyPanel({
  mission,
  busy,
  demoRunning,
  demoProgress,
  onStart,
  onInjectIncident,
  onReoptimize,
  onReset,
  onRunDemo,
  onStopDemo,
}) {
  const missionActive = mission && mission.status !== 'COMPLETED'

  return (
    <aside className="qgc-panel qgc-panel-left glass-panel">
      <div className="qgc-panel-header">
        <span className="qgc-panel-icon">🚨</span> EMERGENCY CONTROL
      </div>

      <div className="qgc-full-demo">
        <button
          className={`qgc-btn qgc-btn-demo ${demoRunning ? 'running' : ''}`}
          onClick={demoRunning ? onStopDemo : onRunDemo}
        >
          {demoRunning ? '■ STOP DEMO' : '🚀 RUN FULL DEMO'}
        </button>
        {demoRunning && (
          <div className="qgc-demo-progress">
            <div className="qgc-demo-progress-bar" style={{ width: `${demoProgress.pct}%` }} />
            <p>{demoProgress.label}</p>
          </div>
        )}
      </div>

      <div className="qgc-divider">MANUAL CONTROLS</div>

      <div className="qgc-field-group">
        <label>Severity</label>
        <div className="qgc-severity-row">
          {SEVERITIES.map((s) => (
            <span key={s} className={`qgc-severity-chip ${s === 'CRITICAL' ? 'active' : ''}`}>{s}</span>
          ))}
        </div>
      </div>

      <div className="qgc-field-group">
        <label>Ambulance</label>
        <div className="qgc-readout">🚑 AMB-01</div>
      </div>
      <div className="qgc-field-group">
        <label>Pickup</label>
        <div className="qgc-readout">Emergency Point (A)</div>
      </div>
      <div className="qgc-field-group">
        <label>Destination</label>
        <div className="qgc-readout">City Hospital (H)</div>
      </div>

      <div className="qgc-btn-stack">
        <button className="qgc-btn qgc-btn-primary" onClick={onStart} disabled={busy || demoRunning || missionActive}>
          START EMERGENCY
        </button>
        <button className="qgc-btn qgc-btn-danger" onClick={onInjectIncident} disabled={busy || demoRunning || !missionActive}>
          ⚠ INJECT TRAFFIC INCIDENT
        </button>
        <button className="qgc-btn qgc-btn-secondary" onClick={onReoptimize} disabled={busy || demoRunning || !missionActive}>
          🔄 RE-OPTIMIZE
        </button>
        <button className="qgc-btn qgc-btn-ghost" onClick={onReset} disabled={demoRunning}>
          RESET SIMULATION
        </button>
      </div>

      {mission && (
        <div className="qgc-mission-card">
          <div className="qgc-mission-card-row">
            <span>Mission</span>
            <span className="mono">{mission.mission_id}</span>
          </div>
          <div className="qgc-mission-card-row">
            <span>Status</span>
            <span className={`qgc-tag qgc-tag-${(mission.status || '').toLowerCase()}`}>{mission.status}</span>
          </div>
        </div>
      )}
    </aside>
  )
}
