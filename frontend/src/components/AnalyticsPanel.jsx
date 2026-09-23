import { useState } from 'react'
import ConvergenceChart from './ConvergenceChart'
import BenchmarkTable from './BenchmarkTable'
import MissionTimeline from './MissionTimeline'
import TrafficStatus from './TrafficStatus'

const TABS = ['Convergence', 'Algorithm Comparison', 'Mission Timeline', 'Traffic Status']

export default function AnalyticsPanel({ convergenceHistory, benchmarkResults, onRunBenchmark, benchmarkRunning, timeline, network }) {
  const [tab, setTab] = useState('Convergence')

  return (
    <section className="qgc-panel qgc-panel-bottom glass-panel">
      <div className="qgc-tabs">
        {TABS.map((t) => (
          <button key={t} className={`qgc-tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      <div className="qgc-tab-content">
        {tab === 'Convergence' && <ConvergenceChart history={convergenceHistory} />}
        {tab === 'Algorithm Comparison' && (
          <BenchmarkTable results={benchmarkResults} onRunBenchmark={onRunBenchmark} running={benchmarkRunning} />
        )}
        {tab === 'Mission Timeline' && <MissionTimeline events={timeline} />}
        {tab === 'Traffic Status' && <TrafficStatus network={network} />}
      </div>
    </section>
  )
}
