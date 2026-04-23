import { getDeviceStatus } from "../api/operatorApi";
import DeviceCard from "../components/DeviceCard";
import MetricCard from "../components/MetricCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ResourceState";
import { useAsyncResource } from "../hooks/useAsyncResource";

export default function DeviceStatusPage() {
  const { data, error, isLoading } = useAsyncResource(() => getDeviceStatus(), []);

  if (isLoading) {
    return <LoadingState label="Loading field device telemetry" />;
  }

  if (error) {
    return <ErrorState error={error} />;
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No devices registered"
        description="As soon as the backend starts exposing field units, they will appear in this view."
      />
    );
  }

  const onlineCount = data.filter((device) => device.status === "online").length;
  const degradedCount = data.filter(
    (device) => device.streamState === "degraded" || device.status === "maintenance",
  ).length;
  const averageHealth = Math.round(
    data.reduce((sum, device) => sum + device.health, 0) / data.length,
  );

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <MetricCard
          label="Registered Units"
          value={data.length}
          hint="Devices currently surfaced by the operator layer."
          accent="blue"
        />
        <MetricCard
          label="Online Units"
          value={onlineCount}
          hint="Devices actively reporting fresh telemetry."
          accent="green"
        />
        <MetricCard
          label="Degraded Units"
          value={degradedCount}
          hint="Streams or hardware requiring inspection soon."
          accent="amber"
        />
        <MetricCard
          label="Avg Health"
          value={`${averageHealth}%`}
          hint="High-level readiness across the visible device fleet."
          accent="red"
        />
      </section>

      <section className="card-grid">
        {data.map((device) => (
          <DeviceCard key={device.deviceId} device={device} />
        ))}
      </section>
    </div>
  );
}
