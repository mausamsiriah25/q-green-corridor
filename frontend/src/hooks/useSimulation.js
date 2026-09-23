import { useEffect, useRef, useState, useCallback } from 'react'
import { api } from '../services/api'

/**
 * Polls /api/ambulance (for smooth movement) and /api/state (for signals,
 * corridor, timeline) at different cadences. Pausable so the Full Demo
 * runner can drive state deterministically without racing the poller.
 */
export function useSimulation({ active }) {
  const [ambulance, setAmbulance] = useState(null)
  const [signals, setSignals] = useState([])
  const [corridor, setCorridor] = useState({ active: false, schedule: [] })
  const [timeline, setTimeline] = useState([])
  const [mission, setMission] = useState(null)
  const [lastIncident, setLastIncident] = useState(null)
  const [commandLog, setCommandLog] = useState([])
  const [navigation, setNavigation] = useState(null)
  const ambTimer = useRef(null)
  const stateTimer = useRef(null)

  const pollAmbulance = useCallback(async () => {
    try {
      const amb = await api.getAmbulance()
      setAmbulance(amb)
    } catch (_) { /* backend may be briefly unavailable during reset */ }
  }, [])

  const pollState = useCallback(async () => {
    try {
      const s = await api.getState()
      setSignals(s.signals || [])
      setCorridor(s.corridor || { active: false, schedule: [] })
      setTimeline(s.timeline || [])
      setMission(s.mission || null)
      setLastIncident(s.last_incident || null)
      setCommandLog(s.command_log || [])
      setNavigation(s.navigation || null)
    } catch (_) { /* noop */ }
  }, [])

  useEffect(() => {
    if (!active) return
    pollAmbulance()
    pollState()
    ambTimer.current = setInterval(pollAmbulance, 400)
    stateTimer.current = setInterval(pollState, 900)
    return () => {
      clearInterval(ambTimer.current)
      clearInterval(stateTimer.current)
    }
  }, [active, pollAmbulance, pollState])

  return {
    ambulance, signals, corridor, timeline, mission, lastIncident,
    commandLog, navigation,
    refreshState: pollState, refreshAmbulance: pollAmbulance,
  }
}
