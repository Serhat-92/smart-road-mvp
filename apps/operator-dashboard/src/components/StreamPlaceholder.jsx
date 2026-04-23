export default function StreamPlaceholder({ stream }) {
  return (
    <article className="panel stream-card">
      <div className="stream-canvas">
        <div className="stream-overlay">
          <span className="mono-label">Live View Placeholder</span>
          <strong>{stream.title}</strong>
          <p>Waiting for RTSP proxy or transcoded HLS feed from the backend.</p>
        </div>
      </div>

      <div className="panel-header">
        <div>
          <p className="eyebrow">{stream.deviceName}</p>
          <h3>{stream.source}</h3>
        </div>
        <span className="status-pill tone-maintenance">{stream.state}</span>
      </div>

      <div className="metric-strip">
        <div>
          <span className="mono-label">Latency</span>
          <strong>{stream.latencyMs} ms</strong>
        </div>
        <div>
          <span className="mono-label">Stream ID</span>
          <strong>{stream.streamId}</strong>
        </div>
      </div>
    </article>
  );
}
