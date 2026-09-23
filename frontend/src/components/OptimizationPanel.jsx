function MetricCard({ label, value, unit, accent }) {
  return (
    <div className="qgc-metric-card" style={accent ? { '--accent': accent } : undefined}>
      <span className="qgc-metric-label">{label}</span>
      <span className="qgc-metric-value">
        {value}
        {unit && <span className="qgc-metric-unit">{unit}</span>}
      </span>
    </div>
  )
}

export default function OptimizationPanel({ optimization, mission, corridor }) {
  const running = optimization?.status === 'running'
  const result = optimization?.result

  const metrics = result?.metrics
  const fitness = result?.fitness
  const label = result?.label || (result?.algorithm ? `${result.algorithm} Route` : '—')

  return (
    <aside className="qgc-panel qgc-panel-right glass-panel">
      <div className="qgc-panel-header">
        <span className="qgc-panel-icon">🧠</span> QPSO OPTIMIZATION
      </div>

      <div className="qgc-algo-status">
        <div className="qgc-algo-row">
          <span>Algorithm</span>
          <span className="mono accent-cyan">QPSO</span>
        </div>
        <div className="qgc-algo-row">
          <span>Population</span>
          <span className="mono">{optimization?.populationSize ?? '—'}</span>
        </div>
        <div className="qgc-algo-row">
          <span>Iteration</span>
          <span className="mono">
            {optimization?.iteration ?? (result ? result.iterations : 0)} / {optimization?.totalIterations ?? (result ? result.iterations : 50)}
          </span>
        </div>
        <div className="qgc-progress-track">
          <div
            className={`qgc-progress-fill ${running ? 'searching' : 'done'}`}
            style={{
              width: `${optimization?.totalIterations ? (100 * (optimization.iteration || 0)) / optimization.totalIterations : (result ? 100 : 0)}%`,
            }}
          />
        </div>
        <div className={`qgc-algo-badge ${running ? 'searching' : result ? 'complete' : ''}`}>
          {running ? 'STATUS: SEARCHING…' : result ? `✓ OPTIMIZATION COMPLETE — ${label}` : 'STATUS: IDLE'}
        </div>
        {result?.used_fallback && (
          <div className="qgc-fallback-warning">⚠ Fallback route used (QPSO candidate was invalid)</div>
        )}
      </div>

      <div className="qgc-metric-grid">
        <MetricCard label="BEST FITNESS" value={fitness ?? '—'} />
        <MetricCard label="ETA" value={metrics ? metrics.travel_time_min.toFixed(1) : '—'} unit="min" accent="var(--accent-green)" />
        <MetricCard label="DISTANCE" value={metrics ? metrics.distance_km.toFixed(2) : '—'} unit="km" />
        <MetricCard label="CONGESTION" value={metrics ? Math.round(metrics.congestion * 100) : '—'} unit="%" accent="var(--accent-amber)" />
        <MetricCard label="SIGNAL DELAY" value={metrics ? metrics.signal_delay_min.toFixed(2) : '—'} unit="min" />
        <MetricCard label="RUNTIME" value={result ? result.runtime_sec.toFixed(3) : '—'} unit="sec" />
      </div>

      <div className="qgc-corridor-status">
        <div className="qgc-panel-subheader">🟢 GREEN CORRIDOR</div>
        <div className={`qgc-corridor-pill ${corridor?.active ? 'active' : ''}`}>
          {corridor?.active ? `ACTIVE — ${corridor.schedule?.length || 0} signal(s)` : 'INACTIVE'}
        </div>
        {corridor?.active && corridor.schedule?.length > 0 && (
          <div className="qgc-corridor-list">
            {corridor.schedule.map((s) => (
              <div key={s.signal_id} className="qgc-corridor-row">
                <span>{s.signal_id}</span>
                <span className="mono">ETA {s.estimated_arrival_min} min</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="qgc-info-box">
        <div className="qgc-info-title">Why QPSO?</div>
        <ul>
          <li>Quantum-inspired search balances exploration &amp; exploitation</li>
          <li>Suited to complex, multi-objective route optimization</li>
          <li>Runs on classical hardware — quantum-inspired, not quantum</li>
          <li>Evaluated live against Dijkstra, A*, PSO &amp; GA baselines</li>
        </ul>
      </div>
    </aside>
  )
}
