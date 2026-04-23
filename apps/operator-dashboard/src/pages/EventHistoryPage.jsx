import { useDeferredValue, useState } from "react";

import { getEventHistory } from "../api/operatorApi";
import HistoryTable from "../components/HistoryTable";
import MetricCard from "../components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ResourceState";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { formatTimestamp } from "../lib/formatters";

const EVENT_REFRESH_INTERVAL_MS = 5000;

export default function EventHistoryPage() {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const { data, error, isLoading, isRefreshing, lastUpdatedAt } = useAsyncResource(
    () => getEventHistory(),
    [],
    { refreshIntervalMs: EVENT_REFRESH_INTERVAL_MS },
  );

  if (isLoading) {
    return <LoadingState label="Loading historical event archive" />;
  }

  if (error && !data) {
    return <ErrorState error={error} />;
  }

  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const filteredItems =
    data?.filter((item) => {
      if (!normalizedQuery) {
        return true;
      }

      return [
        item.eventId,
        item.type,
        item.deviceName,
        item.location,
        item.trackId,
        item.trackLabel,
        item.outcome,
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery);
    }) || [];

  if (filteredItems.length === 0) {
    return (
      <div className="page-stack">
        <div className="search-row panel">
          <input
            className="search-input"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search event id, device, or location"
            value={query}
          />
        </div>
        <EmptyState
          title="No history matches"
          description="Try another search term or clear the query to view the latest archive."
        />
      </div>
    );
  }

  const violationCount = filteredItems.filter(
    (item) => item.type === "speed.violation_alert",
  ).length;
  const evidenceCount = filteredItems.filter((item) => item.evidenceAvailable).length;
  const averageConfidence = Math.round(
    (filteredItems.reduce((sum, item) => sum + item.confidence, 0) / filteredItems.length) * 100,
  );

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <MetricCard
          label="Visible Records"
          value={filteredItems.length}
          hint="Archive entries after deferred search filtering."
          accent="blue"
        />
        <MetricCard
          label="Violations"
          value={violationCount}
          hint="Speed violation alerts in the current result set."
          accent="amber"
        />
        <MetricCard
          label="Evidence"
          value={evidenceCount}
          hint="Records with an attached evidence image."
          accent="green"
        />
        <MetricCard
          label="Avg Confidence"
          value={`${averageConfidence}%`}
          hint="Average confidence across visible records."
          accent="red"
        />
      </section>

      <div className="search-row panel">
        <input
          className="search-input"
          onChange={(inputEvent) => setQuery(inputEvent.target.value)}
          placeholder="Search event id, device, type, track, or location"
          value={query}
        />
      </div>

      <section className="section-heading">
        <div>
          <p className="eyebrow">History Feed</p>
          <h3>Gateway event archive</h3>
          <p className="muted-copy">
            Refreshes every {EVENT_REFRESH_INTERVAL_MS / 1000}s
            {lastUpdatedAt ? ` · last update ${formatTimestamp(lastUpdatedAt)}` : ""}
            {isRefreshing ? " · refreshing..." : ""}
            {error ? ` · latest refresh failed: ${error.message}` : ""}
          </p>
        </div>
      </section>

      <HistoryTable items={filteredItems} />
    </div>
  );
}
