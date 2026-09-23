import { useMemo } from 'react'
import CityMap from './CityMap'

const INSTRUCTION_ICON = {
  LEFT: '⬅️',
  RIGHT: '➡️',
  STRAIGHT: '⬆️',
  ARRIVE: '🏥',
}

function fmtEta(min) {
  if (min == null) return '—'
  if (min < 1) return '<1 min'
  return `${Math.round(min)} min`
}

export default function DriverMode({
  network, mission, ambulance, signals, navigation, busy, onActivate, onDeactivate,
}) {
  const active = mission && mission.status !== 'COMPLETED' && ambulance?.status !== 'IDLE'
  const arrived = ambulance?.status === 'ARRIVED' || mission?.status === 'COMPLETED'

  const corridorActive = (signals || []).some((s) => s.priority_requested)

  const nextManeuverPos = useMemo(() => {
    if (!network?.nodes || !ambulance?.route || ambulance.route_progress_index == null) return null
    const nextNode = ambulance.route[ambulance.route_progress_index + 1]
    return nextNode ? network.nodes[nextNode] : null
  }, [network, ambulance])

  const upcomingSignal = navigation?.upcoming_signal
    ? (signals || []).find((s) => s.node === navigation.upcoming_signal)
    : null

  return (
    <div className="qgc-driver">
      <div className="qgc-driver-map">
        <CityMap
          network={network}
          route={ambulance?.route}
          ambulancePos={ambulance?.position}
          signals={signals}
          mode="driver"
          nextManeuverPos={nextManeuverPos}
        />

        {active && !arrived && navigation && (
          <div className="qgc-driver-instruction">
            <div className="qgc-driver-instruction-icon">{INSTRUCTION_ICON[navigation.instruction_type] || '⬆️'}</div>
            <div className="qgc-driver-instruction-text">
              <div className="qgc-driver-instruction-main">{navigation.text}</div>
              {upcomingSignal && (
                <div className="qgc-driver-instruction-sub">
                  🚦 Approaching {upcomingSignal.signal_id} — {upcomingSignal.current_phase}
                </div>
              )}
            </div>
          </div>
        )}

        {corridorActive && !arrived && (
          <div className="qgc-driver-corridor-badge">🟢 GREEN CORRIDOR: ACTIVE</div>
        )}

        {arrived && (
          <div className="qgc-driver-arrived-banner">🏥 ARRIVED — MISSION COMPLETED</div>
        )}
      </div>

      <div className="qgc-driver-sheet glass-panel">
        {!active ? (
          <>
            <div className="qgc-driver-status-idle">Ambulance AMB-01 · Standing by</div>
            <button
              className="qgc-driver-emergency-btn"
              disabled={busy}
              onClick={onActivate}
            >
              🚨 ACTIVATE EMERGENCY
            </button>
          </>
        ) : (
          <>
            <div className="qgc-driver-top-row">
              <span className={`qgc-driver-emergency-pill ${arrived ? 'done' : 'live'}`}>
                {arrived ? '✅ MISSION COMPLETE' : '🚨 EMERGENCY ACTIVE'}
              </span>
              {!arrived && <span className="qgc-driver-corridor-pill">GREEN CORRIDOR: ACTIVE</span>}
            </div>

            <div className="qgc-driver-stats">
              <div className="qgc-driver-stat">
                <span className="qgc-driver-stat-label">Destination</span>
                <span className="qgc-driver-stat-value">🏥 City Hospital</span>
              </div>
              <div className="qgc-driver-stat">
                <span className="qgc-driver-stat-label">Distance</span>
                <span className="qgc-driver-stat-value">{navigation ? `${navigation.distance_remaining_km} km` : '—'}</span>
              </div>
              <div className="qgc-driver-stat">
                <span className="qgc-driver-stat-label">ETA</span>
                <span className="qgc-driver-stat-value">{navigation ? fmtEta(navigation.eta_min) : '—'}</span>
              </div>
              <div className="qgc-driver-stat">
                <span className="qgc-driver-stat-label">Traffic</span>
                <span className="qgc-driver-stat-value">{ambulance?.status || '—'}</span>
              </div>
            </div>

            <button
              className="qgc-driver-emergency-btn secondary"
              disabled={busy}
              onClick={onDeactivate}
            >
              {arrived ? 'START NEW MISSION' : '⛔ DEACTIVATE EMERGENCY'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
