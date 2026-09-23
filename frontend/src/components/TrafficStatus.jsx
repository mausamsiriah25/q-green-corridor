function stateOf(level) {
  if (level >= 0.8) return { label: 'SEVERE', color: '#ff3b5c' }
  if (level >= 0.55) return { label: 'HEAVY', color: '#ff7a3d' }
  if (level >= 0.3) return { label: 'MODERATE', color: '#ffb020' }
  return { label: 'LOW', color: '#00ffb2' }
}

export default function TrafficStatus({ network }) {
  if (!network?.edges) return <div className="qgc-empty-state">No network data.</div>

  const buckets = { LOW: 0, MODERATE: 0, HEAVY: 0, SEVERE: 0 }
  let blocked = 0
  network.edges.forEach((e) => {
    if (e.blocked) blocked++
    buckets[stateOf(e.traffic_level).label]++
  })
  const total = network.edges.length

  return (
    <div className="qgc-traffic-status">
      <div className="qgc-traffic-bars">
        {Object.entries(buckets).map(([label, count]) => (
          <div key={label} className="qgc-traffic-bar-row">
            <span className="qgc-traffic-bar-label">{label}</span>
            <div className="qgc-traffic-bar-track">
              <div
                className="qgc-traffic-bar-fill"
                style={{ width: `${total ? (100 * count) / total : 0}%`, background: stateOf(label === 'LOW' ? 0 : label === 'MODERATE' ? 0.3 : label === 'HEAVY' ? 0.55 : 0.8).color }}
              />
            </div>
            <span className="mono qgc-traffic-bar-count">{count}</span>
          </div>
        ))}
      </div>
      <div className="qgc-traffic-summary">
        <span>{total} roads monitored</span>
        <span className={blocked > 0 ? 'accent-red' : ''}>{blocked} blocked</span>
      </div>
    </div>
  )
}
