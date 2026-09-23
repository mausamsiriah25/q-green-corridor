import EmergencyPanel from './EmergencyPanel'
import OptimizationPanel from './OptimizationPanel'
import CityMap from './CityMap'
import AnalyticsPanel from './AnalyticsPanel'
import SihAlignment from './SihAlignment'
import CommandLog from './CommandLog'

export default function ControlCenter({
  network, mission, sim, oldRoute, optimization, convergenceHistory,
  benchmarkResults, benchmarkRunning, busy, demoRunning, demoProgress,
  onStart, onInjectIncident, onReoptimize, onReset, onRunDemo, onStopDemo, onRunBenchmark,
}) {
  return (
    <>
      <div className="qgc-main-grid">
        <EmergencyPanel
          mission={mission}
          busy={busy}
          demoRunning={demoRunning}
          demoProgress={demoProgress}
          onStart={onStart}
          onInjectIncident={() => onInjectIncident()}
          onReoptimize={() => onReoptimize()}
          onReset={onReset}
          onRunDemo={onRunDemo}
          onStopDemo={onStopDemo}
        />

        <div className="qgc-center-col">
          <CityMap
            network={network}
            route={mission?.route}
            oldRoute={oldRoute}
            ambulancePos={sim.ambulance?.position}
            signals={sim.signals}
            mode="control"
          />
          <SihAlignment />
        </div>

        <div className="qgc-panel-right">
          <OptimizationPanel optimization={optimization} mission={mission} corridor={sim.corridor} />
          <CommandLog commands={sim.commandLog} />
        </div>
      </div>

      <AnalyticsPanel
        convergenceHistory={convergenceHistory}
        benchmarkResults={benchmarkResults}
        onRunBenchmark={onRunBenchmark}
        benchmarkRunning={benchmarkRunning}
        timeline={sim.timeline}
        network={network}
      />
    </>
  )
}
