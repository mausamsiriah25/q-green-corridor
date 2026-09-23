export default function Header({ online, missionStatus, mode, onModeChange }) {
  return (
    <header className="qgc-header">
      <div className="qgc-header-left">
        <div className="qgc-logo">
          <span className="qgc-logo-icon">◈</span>
          <div>
            <h1>Q-GREEN CORRIDOR</h1>
            <p>Quantum-Inspired Emergency Traffic Optimization</p>
          </div>
        </div>
      </div>

      <div className="qgc-mode-toggle" role="tablist" aria-label="Application mode">
        <button
          className={mode === 'driver' ? 'active' : ''}
          onClick={() => onModeChange('driver')}
          role="tab"
          aria-selected={mode === 'driver'}
        >
          🚑 DRIVER MODE
        </button>
        <button
          className={mode === 'control' ? 'active' : ''}
          onClick={() => onModeChange('control')}
          role="tab"
          aria-selected={mode === 'control'}
        >
          🖥️ CONTROL CENTER
        </button>
      </div>

      <div className="qgc-header-right">
        {missionStatus && (
          <div className="qgc-mission-badge">
            MISSION: <span>{missionStatus}</span>
          </div>
        )}
        <div className="qgc-status">
          <span className={`status-dot ${online ? 'online' : 'critical'}`}></span>
          System Status: <strong>{online ? 'ONLINE' : 'OFFLINE'}</strong>
        </div>
      </div>
    </header>
  )
}
