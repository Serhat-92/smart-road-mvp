import StatusPill from "./StatusPill";
import EvidencePreview from "./EvidencePreview";
import {
  formatEventType,
  formatPercent,
  formatSpeed,
  formatTimestamp,
  formatTrackId,
} from "../lib/formatters";

export default function HistoryTable({ items }) {
  return (
    <div className="table-shell panel">
      <table className="history-table">
        <thead>
          <tr>
            <th>Event</th>
            <th>Track</th>
            <th>Speed</th>
            <th>Confidence</th>
            <th>Evidence</th>
            <th>Outcome</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.eventId}>
              <td>
                <div className="table-title">{formatEventType(item.type)}</div>
                <div className="table-subtitle">{item.deviceName}</div>
              </td>
              <td>
                <div className="table-title">{formatTrackId(item.trackId)}</div>
                <div className="table-subtitle">{item.trackLabel}</div>
              </td>
              <td>
                <div className="table-title">{formatSpeed(item.estimatedSpeed)}</div>
                <div className="table-subtitle">
                  Radar {formatSpeed(item.radarSpeed)} · Limit {formatSpeed(item.speedLimit)}
                </div>
              </td>
              <td>{formatPercent(item.confidence)}</td>
              <td>
                <EvidencePreview event={item} compact />
              </td>
              <td>
                <StatusPill tone={item.outcome}>{item.outcome}</StatusPill>
              </td>
              <td>{formatTimestamp(item.timestamp || item.occurredAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
