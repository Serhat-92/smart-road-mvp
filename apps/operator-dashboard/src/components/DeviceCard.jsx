import StatusPill from "./StatusPill";

export default function DeviceCard({ device }) {
  return (
    <article className="panel device-card">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{device.type.replace("-", " ")}</p>
          <h3>{device.name}</h3>
        </div>
        <StatusPill tone={device.status}>{device.status}</StatusPill>
      </div>

      <dl className="data-list">
        <div>
          <dt>Zone</dt>
          <dd>{device.zone}</dd>
        </div>
        <div>
          <dt>Health</dt>
          <dd>{device.health}%</dd>
        </div>
        <div>
          <dt>Stream</dt>
          <dd>{device.streamState}</dd>
        </div>
        <div>
          <dt>Last Seen</dt>
          <dd>{new Date(device.lastSeen).toLocaleTimeString()}</dd>
        </div>
      </dl>

      <div className="metric-strip">
        <div>
          <span className="mono-label">FPS</span>
          <strong>{device.metrics.fps}</strong>
        </div>
        <div>
          <span className="mono-label">Latency</span>
          <strong>
            {device.metrics.latencyMs === null ? "n/a" : `${device.metrics.latencyMs} ms`}
          </strong>
        </div>
        <div>
          <span className="mono-label">Battery</span>
          <strong>
            {device.metrics.battery === null ? "wired" : `${device.metrics.battery}%`}
          </strong>
        </div>
      </div>
    </article>
  );
}
