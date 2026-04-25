import { useState } from "react";
import StatusPill from "./StatusPill";
import EvidencePreview from "./EvidencePreview";
import { updateEventStatus } from "../api/operatorApi";
import {
  formatEventType,
  formatPercent,
  formatSpeed,
  formatTimestamp,
  formatTrackId,
} from "../lib/formatters";

const STATUS_CONFIG = {
  pending: { label: "Beklemede", tone: "warning" },
  reviewed: { label: "İncelendi", tone: "valid" },
  dismissed: { label: "Geçersiz", tone: "neutral" },
};

export default function EventCard({ event, onStatusChange }) {
  const [operatorStatus, setOperatorStatus] = useState(
    event.operatorStatus || "pending",
  );
  const [isUpdating, setIsUpdating] = useState(false);

  const statusInfo = STATUS_CONFIG[operatorStatus] || STATUS_CONFIG.pending;

  async function handleStatusUpdate(newStatus) {
    const previousStatus = operatorStatus;
    // Optimistic update
    setOperatorStatus(newStatus);
    setIsUpdating(true);

    try {
      await updateEventStatus(event.eventId, newStatus);
      if (onStatusChange) {
        onStatusChange(event.eventId, newStatus);
      }
    } catch (err) {
      console.error("Failed to update event status:", err);
      // Rollback on error
      setOperatorStatus(previousStatus);
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <article className="panel event-card">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{formatEventType(event.type)}</p>
          <h3>{event.location}</h3>
          <p className="muted-copy event-time">{formatTimestamp(event.timestamp)}</p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <StatusPill tone={statusInfo.tone}>{statusInfo.label}</StatusPill>
          <StatusPill tone={event.priority}>{event.priority}</StatusPill>
        </div>
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
          <dt>Plaka</dt>
          <dd><strong>{event.plateNumber || "Tespit Edilemedi"}</strong></dd>
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
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="mono-label">Status</span>
          <strong>{event.status}</strong>
        </div>
        {operatorStatus === "pending" && (
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="status-pill tone-valid"
              style={{ cursor: "pointer", fontSize: "0.75rem" }}
              disabled={isUpdating}
              onClick={() => handleStatusUpdate("reviewed")}
            >
              ✓ İncelendi
            </button>
            <button
              className="status-pill tone-neutral"
              style={{ cursor: "pointer", fontSize: "0.75rem" }}
              disabled={isUpdating}
              onClick={() => handleStatusUpdate("dismissed")}
            >
              ✗ Geçersiz
            </button>
          </div>
        )}
      </footer>
    </article>
  );
}
