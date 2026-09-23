const COMMAND_STYLE = {
  PRIORITY: { icon: '🟢', label: 'PRIORITY ACTIVATED' },
  PREPARE: { icon: '🟡', label: 'PREPARE' },
  NORMAL: { icon: '⚪', label: 'RETURNED TO NORMAL' },
}

export default function CommandLog({ commands }) {
  return (
    <div className="glass-panel qgc-panel">
      <div className="qgc-panel-header">📡 SIGNAL COMMAND LOG</div>
      <div className="qgc-panel-subheader">Live commands issued by the simulated Traffic Control Server</div>
      {(!commands || commands.length === 0) && (
        <div className="qgc-command-log-empty">No signal commands issued yet.</div>
      )}
      <div className="qgc-command-log">
        {(commands || []).map((c, i) => {
          const style = COMMAND_STYLE[c.command] || { icon: '•', label: c.command }
          return (
            <div key={`${c.timestamp}-${i}`} className="qgc-command-log-row">
              <span className="qgc-command-log-time">{c.time}</span>
              <span className="qgc-command-log-icon">{style.icon}</span>
              <span className="qgc-command-log-body">
                <strong>{c.signal_id}</strong> COMMAND: {style.label}
                {c.eta_sec != null && <span className="qgc-command-log-eta"> · ETA {c.eta_sec}s</span>}
                {c.reason && <span className="qgc-command-log-reason"> ({c.reason})</span>}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
