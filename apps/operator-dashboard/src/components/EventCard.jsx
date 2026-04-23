import StatusPill from "./StatusPill";
import EvidencePreview from "./EvidencePreview";
import {
  formatEventType,
  formatPercent,
  formatSpeed,
  formatTimestamp,
  formatTrackId,
} from "../lib/formatters";

export default function EventCard({ event }) {
  return (
    <article className="panel event-card">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{formatEventType(event.type)}</p>
          <h3>{event.location}</h3>
          <p className="muted-copy event-time">{formatTimestamp(event.timestamp)}</p>
        </div>
        <StatusPill tone={event.priority}>{event.priority}</StatusPill>
      </div>

      <div className="event-scoreboard">
        <div>
          <span className="mono-label">Estimated</span>
          <strong>{formatSpeed(event.estimatedSpeed)}</strong>
        </div>
        <div>
          <span className="mono-label">Radar</span>
          <strong>{formatSpeed(event.radarSpeed)}</strong>
        </div>
        <div>
          <span className="mono-label">Limit</span>
          <strong>{formatSpeed(event.speedLimit)}</strong>
        </div>
      </div>

      <dl className="data-list">
        <div>
          <dt>Camera / Device</dt>
          <dd>{event.deviceName}</dd>
        </div>
        <div>
          <dt>Track</dt>
          <dd>{formatTrackId(event.trackId)} · {event.trackLabel}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{formatPercent(event.confidence)}</dd>
        </div>
        <div>
          <dt>Fused Speed</dt>
          <dd>{formatSpeed(event.fusedSpeed)}</dd>
        </div>
      </dl>

      <EvidencePreview event={event} />

      <footer className="panel-footer">
        <span className="mono-label">Status</span>
        <strong>{event.status}</strong>
      </footer>
    </article>
  );
}
