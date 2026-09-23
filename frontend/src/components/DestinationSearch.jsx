import { useEffect, useRef, useState } from 'react'
import { isGoogleMapsConfigured, attachPlacesAutocomplete, geocodeAddress } from '../services/googleMaps'
import { api } from '../services/api'

const SUGGESTIONS = ['City Hospital', 'Ruby Hall Clinic', 'Sassoon General Hospital']

export default function DestinationSearch({ onSetDestination, disabled }) {
  const inputRef = useRef(null)
  const [selected, setSelected] = useState(null)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [serverGeocoding, setServerGeocoding] = useState(false)
  const googleReady = isGoogleMapsConfigured()

  useEffect(() => {
    // find out whether the backend has a server-side Google key configured,
    // so plain-text search still works even without a browser key
    api.getLocationConfig().then((c) => setServerGeocoding(!!c.server_geocoding_available)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!googleReady || !inputRef.current) return undefined
    let unsub = null
    attachPlacesAutocomplete(inputRef.current, (place) => {
      setSelected(place)
      setQuery(place.name)
    }).then((u) => { unsub = u })
    return () => unsub && unsub()
  }, [googleReady])

  const runSearch = async (text) => {
    const q = text ?? query
    if (!q.trim()) return
    setSearching(true)
    try {
      let result = null
      if (googleReady) {
        result = await geocodeAddress(q)
      } else if (serverGeocoding) {
        const r = await api.geocodeServer(q)
        if (r.available) result = { name: q, address: r.address, lat: r.lat, lon: r.lon }
      }
      if (result) {
        setSelected(result)
        setQuery(result.name)
      } else {
        setSelected({ error: true })
      }
    } finally {
      setSearching(false)
    }
  }

  const canSearch = googleReady || serverGeocoding

  return (
    <div className="qgc-dest-search">
      <div className="qgc-dest-search-box">
        <span className="qgc-dest-search-icon">🔍</span>
        <input
          ref={inputRef}
          type="text"
          placeholder={canSearch ? 'Search destination…' : 'Address search needs a Google Maps API key'}
          value={query}
          disabled={disabled || !canSearch}
          onChange={(e) => { setQuery(e.target.value); setSelected(null) }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !googleReady) runSearch() }}
        />
        {!googleReady && canSearch && (
          <button className="qgc-dest-search-go" onClick={() => runSearch()} disabled={searching || disabled}>
            {searching ? '…' : 'Go'}
          </button>
        )}
      </div>

      {!canSearch && (
        <div className="qgc-dest-search-hint">
          Set <code>VITE_GOOGLE_MAPS_API_KEY</code> (browser) or <code>GOOGLE_MAPS_API_KEY</code> (server) to enable
          real address search. Using the simulated ambulance base/hospital for now.
        </div>
      )}

      {canSearch && !selected && (
        <div className="qgc-dest-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="qgc-dest-suggestion-chip" disabled={disabled} onClick={() => { setQuery(s); runSearch(s) }}>
              🏥 {s}
            </button>
          ))}
        </div>
      )}

      {selected && !selected.error && (
        <div className="qgc-dest-result glass-panel">
          <div className="qgc-dest-result-name">{selected.name}</div>
          <div className="qgc-dest-result-address">{selected.address}</div>
          <div className="qgc-dest-result-coords mono">{selected.lat.toFixed(5)}, {selected.lon.toFixed(5)}</div>
          <button
            className="qgc-btn qgc-btn-primary qgc-dest-set-btn"
            disabled={disabled}
            onClick={() => onSetDestination(selected)}
          >
            SET AS DESTINATION
          </button>
        </div>
      )}

      {selected?.error && (
        <div className="qgc-dest-result-error">Couldn't resolve that location — try a different search.</div>
      )}
    </div>
  )
}
