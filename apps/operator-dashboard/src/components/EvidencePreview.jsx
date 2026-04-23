import { useState } from "react";

export default function EvidencePreview({ event, compact = false }) {
  const [hasError, setHasError] = useState(false);

  if (!event.evidenceAvailable || !event.evidenceUrl || hasError) {
    return (
      <div className={compact ? "evidence-card evidence-card-compact" : "evidence-card"}>
        <span className="mono-label">Evidence</span>
        <strong>{event.evidenceAvailable ? "Image unavailable" : "No evidence"}</strong>
        {event.evidencePath ? <p className="evidence-path">{event.evidencePath}</p> : null}
      </div>
    );
  }

  return (
    <div className={compact ? "evidence-card evidence-card-compact" : "evidence-card"}>
      <img
        className={compact ? "evidence-image evidence-image-compact" : "evidence-image"}
        src={event.evidenceUrl}
        alt={`Evidence for ${event.type}`}
        loading="lazy"
        onError={() => setHasError(true)}
      />
      <div className="evidence-caption">
        <span className="mono-label">Evidence</span>
        <strong>{event.trackId !== null && event.trackId !== undefined ? `Track ${event.trackId}` : event.type}</strong>
      </div>
    </div>
  );
}
