/**
 * Google Maps location/address services.
 *
 * IMPORTANT ARCHITECTURAL BOUNDARY:
 * This file is ONLY allowed to talk to Google for address search,
 * geocoding, reverse geocoding, map tiles/visualization, and (optionally,
 * for the illustrative comparison panel) a standard ETA. It must NEVER be
 * used to decide the ambulance's actual emergency route -- that is QPSO's
 * job (backend/routing/qpso.py), operating on our own simulated road
 * graph. See LocationMapper (backend/location/mapper.py) for the
 * boundary between the two.
 *
 * Everything here degrades gracefully: if VITE_GOOGLE_MAPS_API_KEY is
 * missing, or the script fails to load, every exported function resolves
 * to a "not available" result instead of throwing -- callers fall back
 * to the existing Leaflet map / manual address entry.
 */

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''

let loadPromise = null

/** True if a browser API key has been configured at build time. Does not
 * guarantee the script will actually load (network, key restrictions,
 * billing, etc.) -- use loadGoogleMaps() and check the result for that. */
export function isGoogleMapsConfigured() {
  return Boolean(API_KEY)
}

/** Loads the Maps JavaScript API (with the Places library) exactly once,
 * returning the `google.maps` namespace, or null if unavailable. Never
 * rejects -- a failed load resolves to null so callers can fall back. */
export function loadGoogleMaps() {
  if (!isGoogleMapsConfigured()) return Promise.resolve(null)
  if (window.google?.maps) return Promise.resolve(window.google.maps)
  if (loadPromise) return loadPromise

  loadPromise = new Promise((resolve) => {
    const existing = document.getElementById('qgc-google-maps-script')
    if (existing) {
      existing.addEventListener('load', () => resolve(window.google?.maps || null))
      existing.addEventListener('error', () => resolve(null))
      return
    }
    const script = document.createElement('script')
    script.id = 'qgc-google-maps-script'
    script.async = true
    script.defer = true
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(API_KEY)}&libraries=places,geocoding&loading=async`
    script.onload = () => resolve(window.google?.maps || null)
    script.onerror = () => resolve(null)
    document.head.appendChild(script)
  })
  return loadPromise
}

/** Wraps a Places Autocomplete session onto a plain <input>. Returns an
 * unsubscribe function, or null if Google Maps isn't available (caller
 * should fall back to plain-text search + geocodeAddress()). */
export async function attachPlacesAutocomplete(inputEl, onPlaceSelected, options = {}) {
  const maps = await loadGoogleMaps()
  if (!maps || !inputEl) return null

  const autocomplete = new maps.places.Autocomplete(inputEl, {
    fields: ['name', 'formatted_address', 'geometry'],
    ...options,
  })
  const listener = autocomplete.addListener('place_changed', () => {
    const place = autocomplete.getPlace()
    if (!place?.geometry?.location) return
    onPlaceSelected({
      name: place.name || place.formatted_address,
      address: place.formatted_address || place.name,
      lat: place.geometry.location.lat(),
      lon: place.geometry.location.lng(),
    })
  })
  return () => maps.event.removeListener(listener)
}

/** address -> {name, address, lat, lon} | null. Used when Places
 * Autocomplete isn't available/selected (e.g. user just typed and hit
 * enter) but Google Maps did load. */
export async function geocodeAddress(address) {
  const maps = await loadGoogleMaps()
  if (!maps) return null
  return new Promise((resolve) => {
    const geocoder = new maps.Geocoder()
    geocoder.geocode({ address }, (results, status) => {
      if (status !== 'OK' || !results?.[0]) return resolve(null)
      const r = results[0]
      resolve({
        name: r.formatted_address,
        address: r.formatted_address,
        lat: r.geometry.location.lat(),
        lon: r.geometry.location.lng(),
      })
    })
  })
}

/** {lat, lon} -> resolved address string | null */
export async function reverseGeocode(lat, lon) {
  const maps = await loadGoogleMaps()
  if (!maps) return null
  return new Promise((resolve) => {
    const geocoder = new maps.Geocoder()
    geocoder.geocode({ location: { lat, lng: lon } }, (results, status) => {
      if (status !== 'OK' || !results?.[0]) return resolve(null)
      resolve(results[0].formatted_address)
    })
  })
}

/** Standard-roads ETA/distance for the illustrative comparison panel
 * ONLY -- never used for the actual emergency route. Returns
 * {distance_km, duration_min} | null. Costs a Directions API call, so
 * callers must only invoke this when the user explicitly asks to
 * compare (see section 15 "cost / fallback consideration"). */
export async function fetchStandardRouteEstimate(origin, destination) {
  const maps = await loadGoogleMaps()
  if (!maps) return null
  return new Promise((resolve) => {
    const service = new maps.DirectionsService()
    service.route(
      {
        origin: { lat: origin.lat, lng: origin.lon },
        destination: { lat: destination.lat, lng: destination.lon },
        travelMode: maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (status !== 'OK' || !result?.routes?.[0]?.legs?.[0]) return resolve(null)
        const leg = result.routes[0].legs[0]
        resolve({
          distance_km: leg.distance ? Math.round((leg.distance.value / 1000) * 10) / 10 : null,
          duration_min: leg.duration ? Math.round(leg.duration.value / 60) : null,
        })
      }
    )
  })
}
