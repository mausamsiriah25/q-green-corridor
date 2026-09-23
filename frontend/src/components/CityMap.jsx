import { useMemo, useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, CircleMarker, Marker, Popup, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'

function FitBounds({ network }) {
  const map = useMap()
  useEffect(() => {
    if (!network?.nodes) return
    const pts = Object.values(network.nodes).map((n) => [n.lat, n.lon])
    if (pts.length === 0) return
    const bounds = L.latLngBounds(pts)
    map.fitBounds(bounds, { padding: [40, 40] })
  }, [network, map])
  return null
}

/** Driver Mode camera: keeps the ambulance (and a bit of the road ahead)
 * centered, instead of the static whole-city fit used in Control Center. */
function FollowAmbulance({ ambulancePos, nextPos, enabled }) {
  const map = useMap()
  useEffect(() => {
    if (!enabled || !ambulancePos) return
    const target = nextPos
      ? [(ambulancePos.lat + nextPos.lat) / 2, (ambulancePos.lon + nextPos.lon) / 2]
      : [ambulancePos.lat, ambulancePos.lon]
    map.setView(target, Math.max(map.getZoom(), 16), { animate: true, duration: 0.5 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ambulancePos?.lat, ambulancePos?.lon])
  return null
}

const HOSPITAL_ICON = L.divIcon({
  className: 'qgc-map-icon',
  html: '<div class="qgc-icon-hospital">🏥</div>',
  iconSize: [34, 34],
  iconAnchor: [17, 17],
})

const AMBULANCE_ICON = L.divIcon({
  className: 'qgc-map-icon',
  html: '<div class="qgc-icon-ambulance">🚑</div>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
})

function edgeColor(edge, onRoute, onOldRoute) {
  if (edge.blocked) return '#ff3b5c'
  if (onRoute) return '#00ffb2'
  if (onOldRoute) return '#a78bfa'
  if (edge.traffic_level >= 0.7) return '#ff3b5c'
  if (edge.traffic_level >= 0.45) return '#ffb020'
  return 'rgba(140, 155, 180, 0.35)'
}

function edgeWeight(edge, onRoute) {
  if (onRoute) return 5
  if (edge.blocked) return 4
  return 2
}

function routeEdgeSet(route) {
  const set = new Set()
  if (!route) return set
  for (let i = 0; i < route.length - 1; i++) set.add(`${route[i]}->${route[i + 1]}`)
  return set
}

function mergeRoadPairs(edges) {
  const byPair = new Map()
  for (const e of edges) {
    const key = e.source < e.destination ? `${e.source}|${e.destination}` : `${e.destination}|${e.source}`
    const existing = byPair.get(key)
    if (!existing) {
      byPair.set(key, { ...e })
    } else {
      // a physical road has two directional edges; merge so a blocked or
      // congested direction is always reflected on the map regardless of
      // which directional edge happens to be picked as canonical
      existing.blocked = existing.blocked || e.blocked
      existing.traffic_level = Math.max(existing.traffic_level, e.traffic_level)
    }
  }
  return [...byPair.values()]
}

export default function CityMap({ network, route, oldRoute, ambulancePos, signals, mode = 'control', nextManeuverPos }) {
  const isDriver = mode === 'driver'

  const center = useMemo(() => {
    if (!network?.nodes) return [21.1458, 79.0882]
    const vals = Object.values(network.nodes)
    const lat = vals.reduce((s, n) => s + n.lat, 0) / vals.length
    const lon = vals.reduce((s, n) => s + n.lon, 0) / vals.length
    return [lat, lon]
  }, [network])

  const routeSet = useMemo(() => routeEdgeSet(route), [route])
  const oldRouteSet = useMemo(() => routeEdgeSet(oldRoute), [oldRoute])
  const roads = useMemo(() => (network?.edges ? mergeRoadPairs(network.edges) : []), [network])

  if (!network?.nodes) {
    return <div className="qgc-map-loading">Loading simulated city network…</div>
  }

  const signalByNode = Object.fromEntries((signals || []).map((s) => [s.node, s]))

  return (
    <div className={`qgc-map-wrap ${isDriver ? 'qgc-map-driver' : ''}`}>
      <MapContainer
        center={center}
        zoom={isDriver ? 16 : 14}
        className="qgc-map"
        zoomControl={!isDriver}
        attributionControl={false}
      >
        {isDriver ? (
          <FollowAmbulance ambulancePos={ambulancePos} nextPos={nextManeuverPos} enabled={isDriver} />
        ) : (
          <FitBounds network={network} />
        )}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          maxZoom={19}
        />

        {/* roads (one polyline per physical road, merged across both directions) */}
        {roads.map((e) => {
            const u = network.nodes[e.source]
            const v = network.nodes[e.destination]
            if (!u || !v) return null
            const onRoute = routeSet.has(`${e.source}->${e.destination}`) || routeSet.has(`${e.destination}->${e.source}`)
            const onOld = oldRouteSet.has(`${e.source}->${e.destination}`) || oldRouteSet.has(`${e.destination}->${e.source}`)
            return (
              <Polyline
                key={e.edge_id}
                positions={[[u.lat, u.lon], [v.lat, v.lon]]}
                pathOptions={{
                  color: edgeColor(e, onRoute, onOld && !onRoute),
                  weight: edgeWeight(e, onRoute),
                  opacity: e.blocked ? 0.95 : onRoute ? 0.95 : 0.55,
                  dashArray: e.blocked ? '2 6' : onOld && !onRoute ? '4 6' : undefined,
                }}
              >
                <Tooltip sticky>
                  <div className="qgc-map-tooltip">
                    <strong>{e.road_name}</strong>
                    <div>{e.source} → {e.destination}</div>
                    <div>{e.distance} km · {Math.round(e.traffic_level * 100)}% traffic</div>
                    {e.blocked && <div className="qgc-tooltip-blocked">🔴 BLOCKED</div>}
                  </div>
                </Tooltip>
              </Polyline>
            )
          })}

        {/* nodes */}
        {Object.values(network.nodes).map((n) => {
          if (n.type === 'hospital') {
            return (
              <Marker key={n.id} position={[n.lat, n.lon]} icon={HOSPITAL_ICON}>
                <Popup>City Hospital ({n.id})</Popup>
              </Marker>
            )
          }
          if (n.type === 'ambulance_base') {
            return (
              <CircleMarker key={n.id} center={[n.lat, n.lon]} radius={7} pathOptions={{ color: '#37e5ff', fillColor: '#37e5ff', fillOpacity: 0.9 }}>
                <Tooltip>Ambulance Base (A)</Tooltip>
              </CircleMarker>
            )
          }
          if (n.is_signal) {
            const sig = signalByNode[n.id]
            const phase = sig?.current_phase || 'NORMAL'
            const cls = phase === 'PRIORITY' ? 'sig-priority' : phase === 'PREPARE' ? 'sig-prepare' : 'sig-normal'
            return (
              <CircleMarker key={n.id} center={[n.lat, n.lon]} radius={8} className={`qgc-signal-marker ${cls}`}
                pathOptions={{
                  color: phase === 'PRIORITY' ? '#00ffb2' : phase === 'PREPARE' ? '#ffb020' : '#566175',
                  fillColor: phase === 'PRIORITY' ? '#00ffb2' : phase === 'PREPARE' ? '#ffb020' : '#1a2130',
                  fillOpacity: 0.85,
                  weight: 2,
                }}
              >
                <Tooltip>🚦 {sig?.signal_id || n.id} — {phase}</Tooltip>
              </CircleMarker>
            )
          }
          if (isDriver) return null // keep the driver map clean -- signals/base/hospital only
          return (
            <CircleMarker key={n.id} center={[n.lat, n.lon]} radius={3} pathOptions={{ color: 'rgba(150,165,190,0.55)', fillOpacity: 0.6 }} />
          )
        })}

        {ambulancePos && (
          <Marker position={[ambulancePos.lat, ambulancePos.lon]} icon={AMBULANCE_ICON} zIndexOffset={1000}>
            <Tooltip permanent direction="top" offset={[0, -14]} className="qgc-amb-tooltip">AMB-01</Tooltip>
          </Marker>
        )}
      </MapContainer>

      {!isDriver && (
        <div className="qgc-map-legend glass-panel">
          <div><span className="dot" style={{ background: '#00ffb2' }} /> Optimized route</div>
          <div><span className="dot" style={{ background: '#a78bfa' }} /> Previous route</div>
          <div><span className="dot" style={{ background: '#ff3b5c' }} /> Blocked / severe</div>
          <div><span className="dot" style={{ background: '#ffb020' }} /> Congested</div>
          <div><span className="dot" style={{ background: 'rgba(140,155,180,0.6)' }} /> Normal road</div>
        </div>
      )}
    </div>
  )
}
