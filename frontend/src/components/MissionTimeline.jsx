export default function MissionTimeline({ events }) {
  if (!events || events.length === 0) {
    return <div className="qgc-empty-state">No mission events yet. Start an emergency to begin logging.</div>
  }
  return (
    <div className="qgc-timeline scrollbar-thin">
      {events.slice().reverse().map((e, i) => (
        <div key={i} className="qgc-timeline-row">
          <span className="mono qgc-timeline-time">{e.time}</span>
          <span className="qgc-timeline-icon">{e.icon}</span>
          <span className="qgc-timeline-msg">{e.message}</span>
        </div>
      ))}
    </div>
  )
}
