import { getLiveStreams } from "../api/operatorApi";
import MetricCard from "../components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ResourceState";
import StreamPlaceholder from "../components/StreamPlaceholder";
import { useAsyncResource } from "../hooks/useAsyncResource";

export default function LiveStreamPage() {
  const { data, error, isLoading } = useAsyncResource(() => getLiveStreams(), []);

  if (isLoading) {
    return <LoadingState label="Preparing live stream placeholders" />;
  }

  if (error) {
    return <ErrorState error={error} />;
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No live stream sources"
        description="Connect camera streams through the backend and the live wall will populate here."
      />
    );
  }

  const averageLatency = Math.round(
    data.reduce((sum, stream) => sum + stream.latencyMs, 0) / data.length,
  );

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <MetricCard
          label="Visible Stream Slots"
          value={data.length}
          hint="Tiles prepared for backend-provided operator video feeds."
          accent="blue"
        />
        <MetricCard
          label="Avg Latency"
          value={`${averageLatency} ms`}
          hint="Mock transport signal until HLS or WebRTC is connected."
          accent="green"
        />
        <MetricCard
          label="Mode"
          value="Placeholder"
          hint="UI is ready to bind to backend session and stream metadata."
          accent="amber"
        />
      </section>

      <div className="stream-grid">
        {data.map((stream) => (
          <StreamPlaceholder key={stream.streamId} stream={stream} />
        ))}
      </div>
    </div>
  );
}
