import { useState } from 'react'
import CityMap from './CityMap'
import GoogleCityMap from './GoogleCityMap'
import { isGoogleMapsConfigured } from '../services/googleMaps'

const DEFAULT_PROVIDER = (import.meta.env.VITE_MAP_PROVIDER || 'leaflet').toLowerCase()

/**
 * MAP_PROVIDER switch (section 16). If MAP_PROVIDER=google and a browser
 * key is configured, Google Maps is used as the initial basemap;
 * otherwise (missing key, or MAP_PROVIDER=leaflet) it falls back to the
 * existing Leaflet map. The user can always toggle manually when Google
 * is available -- the map is never left broken.
 */
export default function MapView(props) {
  const googleAvailable = isGoogleMapsConfigured()
  const [provider, setProvider] = useState(
    DEFAULT_PROVIDER === 'google' && googleAvailable ? 'google' : 'leaflet'
  )
  const useGoogle = provider === 'google' && googleAvailable

  return (
    <div className="qgc-mapview">
      {googleAvailable && (
        <div className="qgc-map-provider-toggle">
          <button
            className={provider === 'leaflet' ? 'active' : ''}
            onClick={() => setProvider('leaflet')}
          >
            Simulated
          </button>
          <button
            className={provider === 'google' ? 'active' : ''}
            onClick={() => setProvider('google')}
          >
            🗺️ Google Maps
          </button>
        </div>
      )}
      {useGoogle ? <GoogleCityMap {...props} /> : <CityMap {...props} />}
      <div className="qgc-map-source-label">
        {useGoogle ? 'Location services: Google Maps Platform' : 'Map: simulated network'} · Emergency routing: QPSO
      </div>
    </div>
  )
}
