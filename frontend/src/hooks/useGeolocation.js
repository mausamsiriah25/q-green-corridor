import { useCallback, useState } from 'react'

/**
 * Wraps navigator.geolocation with permission/timeout/unavailable
 * handling. Never throws -- on any failure `status` becomes 'unavailable'
 * and callers should fall back to the existing simulated ambulance
 * starting location (per "Current Location" spec: GPS unavailable must
 * never block the prototype from running).
 */
export function useGeolocation() {
  const [status, setStatus] = useState('idle') // idle | requesting | granted | denied | unavailable | timeout
  const [position, setPosition] = useState(null) // { lat, lon, accuracy }
  const [error, setError] = useState(null)

  const request = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setStatus('unavailable')
      setError('Geolocation not supported by this browser')
      return
    }
    setStatus('requesting')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        })
        setStatus('granted')
      },
      (err) => {
        // err.code: 1 = PERMISSION_DENIED, 2 = POSITION_UNAVAILABLE, 3 = TIMEOUT
        if (err.code === 1) setStatus('denied')
        else if (err.code === 3) setStatus('timeout')
        else setStatus('unavailable')
        setError(err.message)
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
    )
  }, [])

  return { status, position, error, request }
}
