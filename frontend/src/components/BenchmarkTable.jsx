export default function BenchmarkTable({ results, onRunBenchmark, running }) {
  return (
    <div>
      <div className="qgc-benchmark-header">
        <button className="qgc-btn qgc-btn-secondary qgc-btn-sm" onClick={onRunBenchmark} disabled={running}>
          {running ? 'Running…' : '▶ Run Benchmark'}
        </button>
        {(!results || results.length === 0) && <span className="qgc-hint">No benchmark run yet.</span>}
      </div>
      {results && results.length > 0 && (
        <table className="qgc-table">
          <thead>
            <tr>
              <th>Algorithm</th>
              <th>Feasible</th>
              <th>ETA (min)</th>
              <th>Distance (km)</th>
              <th>Congestion</th>
              <th>Fitness</th>
              <th>Runtime (s)</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.algorithm} className={r.algorithm === 'QPSO' ? 'qgc-row-highlight' : ''}>
                <td className="mono">{r.algorithm}</td>
                <td>{r.feasible ? '✓' : '✗'}</td>
                <td>{r.metrics ? r.metrics.travel_time_min.toFixed(2) : '—'}</td>
                <td>{r.metrics ? r.metrics.distance_km.toFixed(2) : '—'}</td>
                <td>{r.metrics ? `${Math.round(r.metrics.congestion * 100)}%` : '—'}</td>
                <td className="mono">{r.fitness ?? '—'}</td>
                <td className="mono">{r.runtime_sec?.toFixed(4) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
