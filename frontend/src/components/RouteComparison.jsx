import { useState } from 'react'
import { isGoogleMapsConfigured, fetchStandardRouteEstimate } from '../services/googleMaps'

function originDestCoords(mission, network) {
  if (!mission || !network?.nodes) return null
  const originNode = network.nodes[mission.pickup]
  const destNode = network.nodes[mission.destination]
  if (!originNode || !destNode) return null
  return {
    origin: mission.location?.pickup
      ? { lat: mission.location.pickup.lat, lon: mission.location.pickup.lon }
      : { lat: originNode.lat, lon: originNode.lon },
    destination: mission.location?.destination
      ? { lat: mission.location.destination.lat, lon: mission.location.destination.lon }
      : { lat: destNode.lat, lon: destNode.lon },
  }
}

/**
 * Optional Route Comparison panel (spec sections 9-10). Fetches a
 * standard-roads ETA/distance from Google Directions ONLY when the user
 * explicitly clicks compare -- never polled, never fabricated. If Google
 * Maps isn't configured, or the request fails, shows "Unavailable" and
 * nothing else.
 */
export default function RouteComparison({ mission, network, qpsoMetrics }) {
  const [google, setGoogle] = useState(null) // null = not fetched, {} = fetched (or failed -> {unavailable:true})
  const [loading, setLoading] = useState(false)
  const available = isGoogleMapsConfigured()
  const coords = originDestCoords(mission, network)

  const runCompare = async () => {
    if (!coords) return
    setLoading(true)
    try {
      const estimate = await fetchStandardRouteEstimate(coords.origin, coords.destination)
      setGoogle(estimate || { unavailable: true })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="qgc-route-compare glass-panel">
      <div className="qgc-panel-subheader">🗺️ ROUTE COMPARISON <span className="qgc-illustrative-tag">Illustrative simulation</span></div>

      {!available && (
        <div className="qgc-dest-search-hint">Set VITE_GOOGLE_MAPS_API_KEY to enable this comparison.</div>
      )}

      {available && (
        <>
          <button
            className="qgc-btn qgc-btn-secondary qgc-compare-btn"
            disabled={!coords || !qpsoMetrics || loading}
            onClick={runCompare}
          >
            {loading ? 'Comparing…' : 'Compare with Google Maps'}
          </button>

          <div className="qgc-compare-grid">
            <div className="qgc-compare-col">
              <div className="qgc-compare-col-title">Google Route</div>
              {google === null && <div className="qgc-compare-value muted">Not compared yet</div>}
              {google?.unavailable && <div className="qgc-compare-value muted">Unavailable</div>}
              {google && !google.unavailable && (
                <>
                  <div className="qgc-compare-value">{google.duration_min} min</div>
                  <div className="qgc-compare-sub">{google.distance_km} km</div>
                </>
              )}
            </div>
            <div className="qgc-compare-col">
              <div className="qgc-compare-col-title accent-green">QPSO Emergency Route</div>
              {qpsoMetrics ? (
                <>
                  <div className="qgc-compare-value accent-green">{qpsoMetrics.travel_time_min.toFixed(1)} min</div>
                  <div className="qgc-compare-sub">{qpsoMetrics.distance_km.toFixed(2)} km</div>
                </>
              ) : (
                <div className="qgc-compare-value muted">No route yet</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
