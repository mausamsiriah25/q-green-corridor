import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function ConvergenceChart({ history }) {
  if (!history || history.length === 0) {
    return <div className="qgc-empty-state">Run optimization to see the QPSO convergence curve.</div>
  }
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={history} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="iteration" stroke="#566175" tick={{ fontSize: 11 }} label={{ value: 'Iteration', position: 'insideBottom', offset: -4, fill: '#566175', fontSize: 11 }} />
        <YAxis stroke="#566175" tick={{ fontSize: 11 }} label={{ value: 'Best Fitness', angle: -90, position: 'insideLeft', fill: '#566175', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: '#0f1520', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#8b98ab' }}
        />
        <Line type="monotone" dataKey="best_fitness" stroke="#00ffb2" strokeWidth={2} dot={false} isAnimationActive={true} />
      </LineChart>
    </ResponsiveContainer>
  )
}
