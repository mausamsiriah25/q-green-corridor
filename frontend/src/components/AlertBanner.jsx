export default function AlertBanner({ alert, onDismiss }) {
  if (!alert) return null
  return (
    <div className={`qgc-alert-banner qgc-alert-${alert.type || 'info'}`} onClick={onDismiss}>
      <span className="qgc-alert-icon">{alert.icon || 'ℹ'}</span>
      <span>{alert.message}</span>
    </div>
  )
}
