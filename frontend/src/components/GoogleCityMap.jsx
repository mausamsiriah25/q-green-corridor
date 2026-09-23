import { useEffect, useRef, useState } from 'react'
import { loadGoogleMaps } from '../services/googleMaps'

function edgeColor(edge, onRoute) {
  if (edge.blocked) return '#ff3b5c'
  if (onRoute) return '#00ffb2'
  if (edge.traffic_level >= 0.7) return '#ff3b5c'
  if (edge.traffic_level >= 0.45) return '#ffb020'
  return '#8c9bb4'
}

function routeEdgeSet(route) {
  const set = new Set()
  if (!route) return set
  for (let i = 0; i < route.length - 1; i++) set.add(`${route[i]}->${route[i + 1]}`)
  return set
}

/**
 * Renders the SAME simulated road network + QPSO route geometry as
 * CityMap.jsx, but on a real Google Maps basemap instead of Leaflet/
 * Carto tiles -- for real-world geographic context (section 7). This
 * never calls Google's Directions/Routes API to draw the route; the
 * polyline is our own optimized route, drawn manually.
 *
 * Falls back to rendering nothing (parent should not mount this without
 * checking isGoogleMapsConfigured() first) if the SDK fails to load.
 */
export default function GoogleCityMap({
  network, route, ambulancePos, signals, mode = 'control', destinationPin,
}) {
  const isDriver = mode === 'driver'
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const overlaysRef = useRef([])
  const ambMarkerRef = useRef(null)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)

  // init map once
  useEffect(() => {
    let cancelled = false
    loadGoogleMaps().then((maps) => {
      if (cancelled) return
      if (!maps || !containerRef.current) { setFailed(true); return }
      mapRef.current = new maps.Map(containerRef.current, {
        zoom: isDriver ? 16 : 14,
        center: { lat: 21.1458, lng: 79.0882 },
        disableDefaultUI: isDriver,
        styles: DARK_STYLE,
      })
      setReady(true)
    })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // draw / redraw roads + signals + destination pin whenever network/route changes
  useEffect(() => {
    if (!ready || !window.google?.maps || !network?.nodes) return
    const maps = window.google.maps
    const map = mapRef.current

    overlaysRef.current.forEach((o) => o.setMap(null))
    overlaysRef.current = []

    const routeSet = routeEdgeSet(route)
    const seen = new Set()
    for (const e of Object.values(network.edges || {})) {
      const key = e.source < e.destination ? `${e.source}|${e.destination}` : `${e.destination}|${e.source}`
      if (seen.has(key)) continue
      seen.add(key)
      const u = network.nodes[e.source]
      const v = network.nodes[e.destination]
      if (!u || !v) continue
      const onRoute = routeSet.has(`${e.source}->${e.destination}`) || routeSet.has(`${e.destination}->${e.source}`)
      const line = new maps.Polyline({
        path: [{ lat: u.lat, lng: u.lon }, { lat: v.lat, lng: v.lon }],
        strokeColor: edgeColor(e, onRoute),
        strokeWeight: onRoute ? 5 : 2,
        strokeOpacity: e.blocked ? 0.95 : onRoute ? 0.95 : 0.5,
        map,
      })
      overlaysRef.current.push(line)
    }

    const signalByNode = Object.fromEntries((signals || []).map((s) => [s.node, s]))
    for (const n of Object.values(network.nodes)) {
      if (n.type === 'hospital') {
        overlaysRef.current.push(new maps.Marker({
          position: { lat: n.lat, lng: n.lon }, map, label: '🏥', title: 'City Hospital',
        }))
      } else if (n.is_signal) {
        const phase = signalByNode[n.id]?.current_phase || 'NORMAL'
        const color = phase === 'PRIORITY' ? '#00ffb2' : phase === 'PREPARE' ? '#ffb020' : '#566175'
        overlaysRef.current.push(new maps.Marker({
          position: { lat: n.lat, lng: n.lon }, map,
          icon: { path: maps.SymbolPath.CIRCLE, scale: 6, fillColor: color, fillOpacity: 0.9, strokeWeight: 1, strokeColor: '#0a0e14' },
          title: `Signal ${signalByNode[n.id]?.signal_id || n.id} — ${phase}`,
        }))
      }
    }

    if (destinationPin) {
      overlaysRef.current.push(new maps.Marker({
        position: { lat: destinationPin.lat, lng: destinationPin.lon },
        map,
        label: '📍',
        title: destinationPin.name || 'Selected destination',
      }))
    }

    if (!isDriver) {
      const bounds = new maps.LatLngBounds()
      Object.values(network.nodes).forEach((n) => bounds.extend({ lat: n.lat, lng: n.lon }))
      map.fitBounds(bounds, 40)
    }
  }, [ready, network, route, signals, destinationPin, isDriver])

  // ambulance marker + follow camera
  useEffect(() => {
    if (!ready || !window.google?.maps || !ambulancePos) return
    const maps = window.google.maps
    const map = mapRef.current
    const pos = { lat: ambulancePos.lat, lng: ambulancePos.lon }
    if (!ambMarkerRef.current) {
      ambMarkerRef.current = new maps.Marker({ position: pos, map, label: '🚑', zIndex: 999 })
    } else {
      ambMarkerRef.current.setPosition(pos)
    }
    if (isDriver) map.panTo(pos)
  }, [ready, ambulancePos, isDriver])

  if (failed) {
    return <div className="qgc-map-loading">Google Maps unavailable — switch back to Simulated view.</div>
  }

  return (
    <div className={`qgc-map-wrap ${isDriver ? 'qgc-map-driver' : ''}`}>
      <div ref={containerRef} className="qgc-map" />
      {!ready && <div className="qgc-map-loading">Loading Google Maps…</div>}
    </div>
  )
}

// A dark basemap style roughly matching the existing Carto "dark_all"
// look, so switching providers doesn't jar the demo visually.
const DARK_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#0f1520' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0a0e14' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#8b98ab' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#1a2130' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0a0e14' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
]
