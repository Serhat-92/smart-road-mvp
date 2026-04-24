import { getActiveEvents, mapGatewayEvent } from "../api/operatorApi";
import EventCard from "../components/EventCard";
import MetricCard from "../components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ResourceState";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useWebSocket } from "../hooks/useWebSocket";
import { formatTimestamp } from "../lib/formatters";
import { useEffect, useState } from "react";

const EVENT_REFRESH_INTERVAL_MS = 5000;

export default function ActiveEventsPage() {
  const { data: initialData, error: initialError, isLoading } = useAsyncResource(
    () => getActiveEvents(),
    [],
  );

  const [events, setEvents] = useState([]);
  const { data: wsEvent, isConnected: isWsConnected } = useWebSocket("/ws/events");

  // Fallback polling if WS disconnected
  const { data: polledData, isRefreshing, lastUpdatedAt } = useAsyncResource(
    () => getActiveEvents(),
    [],
    { refreshIntervalMs: isWsConnected ? 0 : EVENT_REFRESH_INTERVAL_MS },
  );

  useEffect(() => {
    if (initialData && events.length === 0) {
      setEvents(initialData);
    }
  }, [initialData]);

  useEffect(() => {
    if (polledData && !isWsConnected) {
      setEvents(polledData);
    }
  }, [polledData, isWsConnected]);

  useEffect(() => {
    if (wsEvent) {
      const mappedEvent = mapGatewayEvent(wsEvent);
      setEvents((prev) => {
        // Prevent duplicates
        if (prev.some((e) => e.eventId === mappedEvent.eventId)) return prev;
        return [mappedEvent, ...prev].slice(0, 100); // Keep last 100
      });
    }
  }, [wsEvent]);

  if (isLoading) {
    return <LoadingState label="Loading active event feed" />;
  }

  if (initialError && events.length === 0) {
    return <ErrorState error={initialError} />;
  }

  if (events.length === 0) {
    return (
      <EmptyState
        title="No active events"
        description="The field network is quiet right now. New alerts will appear here as they arrive."
      />
    );
  }

  const violationCount = events.filter((item) => item.type === "speed.violation_alert").length;
  const evidenceCount = events.filter((item) => item.evidenceAvailable).length;
  const averageConfidence = Math.round(
    (events.reduce((sum, item) => sum + item.confidence, 0) / Math.max(events.length, 1)) * 100,
  );

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <MetricCard
          label="Live Events"
          value={events.length}
          hint="Fetched directly from the gateway event feed."
          accent="amber"
        />
        <MetricCard
          label="Violations"
          value={violationCount}
          hint="Speed violation alerts currently visible."
          accent="red"
        />
        <MetricCard
          label="Evidence"
          value={evidenceCount}
          hint="Events carrying an evidence image path."
          accent="blue"
        />
        <MetricCard
          label="Avg Confidence"
          value={`${averageConfidence}%`}
          hint="Confidence of active fusion decisions in the queue."
          accent="green"
        />
      </section>

      <section className="section-heading">
        <div>
          <p className="eyebrow">Near Real Time</p>
          <h3>Active gateway events</h3>
          <p className="muted-copy">
            {isWsConnected ? "Live via WebSocket" : `Refreshes every ${EVENT_REFRESH_INTERVAL_MS / 1000}s`}
            {!isWsConnected && lastUpdatedAt ? ` · last update ${formatTimestamp(lastUpdatedAt)}` : ""}
            {!isWsConnected && isRefreshing ? " · refreshing..." : ""}
          </p>
        </div>
      </section>

      <section className="card-grid">
        {events.map((event) => (
          <EventCard key={event.eventId} event={event} />
        ))}
      </section>
    </div>
  );
}
