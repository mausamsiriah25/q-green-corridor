const ITEMS = [
  'Graph-based network modelling',
  'Dynamic traffic conditions',
  'Shortest-path optimization',
  'Metaheuristic optimization',
  'QPSO (quantum-inspired)',
  'Constraint handling',
  'Convergence analysis',
  'Benchmarking',
  'Scalability-ready architecture',
]

export default function SihAlignment() {
  return (
    <div className="qgc-sih-panel glass-panel">
      <div className="qgc-panel-subheader">SIH PS 26137 ALIGNMENT</div>
      <ul className="qgc-sih-list">
        {ITEMS.map((i) => (
          <li key={i}>
            <span className="accent-green">✓</span> {i}
          </li>
        ))}
      </ul>
      <p className="qgc-disclaimer">
        Quantum-inspired optimization executed on classical hardware. Simulated intelligent traffic
        environment — near-optimal route optimization, experimental benchmark, green corridor simulation.
      </p>
    </div>
  )
}
