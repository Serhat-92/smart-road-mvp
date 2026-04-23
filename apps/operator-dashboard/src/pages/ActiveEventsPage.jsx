import { getActiveEvents } from "../api/operatorApi";
import EventCard from "../components/EventCard";
import MetricCard from "../components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ResourceState";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { formatTimestamp } from "../lib/formatters";

const EVENT_REFRESH_INTERVAL_MS = 5000;

export default function ActiveEventsPage() {
  const { data, error, isLoading, isRefreshing, lastUpdatedAt } = useAsyncResource(
    () => getActiveEvents(),
    [],
    { refreshIntervalMs: EVENT_REFRESH_INTERVAL_MS },
  );

  if (isLoading) {
    return <LoadingState label="Loading active event feed" />;
  }

  if (error && !data) {
    return <ErrorState error={error} />;
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No active events"
        description="The field network is quiet right now. New alerts will appear here as they arrive."
      />
    );
  }

  const violationCount = data.filter((item) => item.type === "speed.violation_alert").length;
  const evidenceCount = data.filter((item) => item.evidenceAvailable).length;
  const averageConfidence = Math.round(
    (data.reduce((sum, item) => sum + item.confidence, 0) / data.length) * 100,
  );

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <MetricCard
          label="Live Events"
          value={data.length}
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
            Refreshes every {EVENT_REFRESH_INTERVAL_MS / 1000}s
            {lastUpdatedAt ? ` · last update ${formatTimestamp(lastUpdatedAt)}` : ""}
            {isRefreshing ? " · refreshing..." : ""}
            {error ? ` · latest refresh failed: ${error.message}` : ""}
          </p>
        </div>
      </section>

      <section className="card-grid">
        {data.map((event) => (
          <EventCard key={event.eventId} event={event} />
        ))}
      </section>
    </div>
  );
}
