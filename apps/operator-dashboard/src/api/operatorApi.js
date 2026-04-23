const DEFAULT_API_BASE_URL = "http://127.0.0.1:8080";
const EVIDENCE_PROXY_PATH = "/local-evidence";

export const apiConfig = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(
    /\/$/,
    "",
  ),
  useMockApi: import.meta.env.VITE_USE_MOCK_API === "true",
  evidenceProxyPath: EVIDENCE_PROXY_PATH,
};

async function getMockData() {
  const module = await import("./mockData");
  return module;
}

async function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function clonePayload(payload) {
  return JSON.parse(JSON.stringify(payload));
}

async function withMock(loader) {
  await delay(220);
  return clonePayload(loader());
}

async function requestJson(path, searchParams) {
  const url = new URL(path, apiConfig.apiBaseUrl);
  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await fetch(url.toString(), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

function unwrapItems(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }

  return [];
}

function mapSeverityToPriority(severity) {
  if (severity === "critical") {
    return "critical";
  }
  if (severity === "warning") {
    return "warning";
  }
  return "neutral";
}

function deriveLocation(event, payload) {
  return (
    payload?.metadata?.location ||
    payload?.metadata?.zone ||
    payload?.camera_id ||
    payload?.frame?.source ||
    event.device_id ||
    "Unassigned corridor"
  );
}

function deriveDeviceName(event, payload) {
  return (
    payload?.camera_id ||
    payload?.metadata?.device_name ||
    event.device_id ||
    payload?.source_service ||
    payload?.source ||
    "Unknown device"
  );
}

function deriveTrackLabel(payload) {
  return (
    payload?.label ||
    payload?.visual?.label ||
    payload?.detections?.[0]?.label ||
    "vehicle"
  );
}

function deriveConfidence(payload) {
  return payload?.confidence_score ?? payload?.visual?.confidence ?? payload?.detections?.[0]?.confidence ?? 0;
}

function deriveTimestamp(event, payload) {
  return (
    payload?.timestamp ||
    event.occurred_at ||
    payload?.emitted_at ||
    event.created_at ||
    null
  );
}

function deriveTrackId(payload) {
  return payload?.track_id ?? payload?.visual?.track_id ?? payload?.detections?.[0]?.track_id ?? null;
}

function deriveEstimatedSpeed(payload) {
  return payload?.estimated_speed ?? payload?.visual?.speed ?? 0;
}

function deriveRadarSpeed(payload) {
  return payload?.radar_speed ?? payload?.radar?.absolute_speed ?? null;
}

function deriveFusedSpeed(payload) {
  return payload?.fused_speed ?? payload?.visual_speed ?? payload?.estimated_speed ?? payload?.metadata?.speed ?? 0;
}

function deriveSpeedLimit(payload) {
  return payload?.speed_limit ?? payload?.road_speed_limit ?? payload?.metadata?.speed_limit ?? null;
}

function deriveViolationAmount(payload, estimatedSpeed, speedLimit) {
  if (typeof payload?.violation_amount === "number") {
    return payload.violation_amount;
  }
  if (typeof estimatedSpeed === "number" && typeof speedLimit === "number") {
    return Math.max(estimatedSpeed - speedLimit, 0);
  }
  return null;
}

function deriveEvidencePath(payload) {
  return payload?.image_evidence_path || null;
}

function deriveEvidenceUrl(evidencePath) {
  if (!evidencePath) {
    return null;
  }

  if (/^https?:\/\//i.test(evidencePath)) {
    return evidencePath;
  }

  const proxyUrl = new URL(EVIDENCE_PROXY_PATH, window.location.origin);
  proxyUrl.searchParams.set("path", evidencePath);
  return proxyUrl.toString();
}

function deriveWorkflowStatus(event, payload) {
  return (
    payload?.metadata?.workflow_status ||
    (event.event_type === "speed.violation_alert" ? "violation" : "observation")
  );
}

function deriveOutcome(event, payload) {
  if (payload?.metadata?.outcome) {
    return payload.metadata.outcome;
  }
  if (event.event_type === "speed.violation_alert") {
    return "violation";
  }
  if (event.event_type === "fused.vehicle_event") {
    return "matched";
  }
  return "recorded";
}

function mapGatewayEvent(event) {
  const payload = event.payload || {};
  const estimatedSpeed = deriveEstimatedSpeed(payload);
  const radarSpeed = deriveRadarSpeed(payload);
  const fusedSpeed = deriveFusedSpeed(payload);
  const speedLimit = deriveSpeedLimit(payload);
  const evidencePath = deriveEvidencePath(payload);

  return {
    eventId: String(event.id || payload.event_id || `${event.event_type}-${event.occurred_at}`),
    type: payload.event_type || event.event_type,
    priority: mapSeverityToPriority(event.severity),
    location: deriveLocation(event, payload),
    deviceName: deriveDeviceName(event, payload),
    trackLabel: deriveTrackLabel(payload),
    status: deriveWorkflowStatus(event, payload),
    outcome: deriveOutcome(event, payload),
    timestamp: deriveTimestamp(event, payload),
    occurredAt: event.occurred_at || deriveTimestamp(event, payload),
    updatedAt: event.created_at || event.occurred_at || deriveTimestamp(event, payload),
    confidence: deriveConfidence(payload),
    trackId: deriveTrackId(payload),
    estimatedSpeed,
    radarSpeed,
    fusedSpeed,
    speedLimit,
    violationAmount: deriveViolationAmount(payload, estimatedSpeed, speedLimit),
    evidencePath,
    evidenceUrl: deriveEvidenceUrl(evidencePath),
    evidenceAvailable: Boolean(evidencePath),
    sourceService: payload?.source_service || null,
    rawEvent: event,
  };
}

function sortByUpdatedDescending(left, right) {
  return new Date(right.updatedAt || 0) - new Date(left.updatedAt || 0);
}

function sortByOccurredDescending(left, right) {
  return new Date(right.occurredAt || 0) - new Date(left.occurredAt || 0);
}

function mapDeviceStatus(status) {
  if (status === "active") {
    return "online";
  }
  if (status === "inactive") {
    return "offline";
  }
  return status || "maintenance";
}

function deriveDeviceHealth(metadata, status) {
  if (typeof metadata?.health === "number") {
    return metadata.health;
  }
  if (status === "active") {
    return 95;
  }
  if (status === "inactive") {
    return 35;
  }
  return 70;
}

function deriveStreamState(metadata, status) {
  if (metadata?.stream_state) {
    return metadata.stream_state;
  }
  if (status === "active") {
    return "stable";
  }
  if (status === "inactive") {
    return "unavailable";
  }
  return "degraded";
}

function mapGatewayDevice(device) {
  const metadata = device.metadata || {};
  return {
    deviceId: device.device_id,
    name: device.name || device.device_id,
    type: device.kind || "device",
    zone: metadata.zone || metadata.location || "Unassigned zone",
    status: mapDeviceStatus(device.status),
    health: deriveDeviceHealth(metadata, device.status),
    streamState: deriveStreamState(metadata, device.status),
    lastSeen: device.updated_at || device.registered_at,
    metrics: {
      fps: metadata.fps ?? 0,
      latencyMs: metadata.latency_ms ?? null,
      battery: metadata.battery ?? null,
    },
    source: metadata.stream_source || metadata.rtsp_url || null,
  };
}

function mapDeviceToStream(device) {
  return {
    streamId: `stream-${device.deviceId}`,
    title: `${device.name} live view`,
    source: device.source || "RTSP source pending",
    state: "placeholder",
    latencyMs: device.metrics.latencyMs ?? 0,
    deviceName: device.name,
  };
}

export async function getActiveEvents() {
  if (apiConfig.useMockApi) {
    const { activeEvents } = await getMockData();
    return withMock(() => activeEvents);
  }

  const payload = await requestJson("/events");
  return unwrapItems(payload)
    .map((event) => mapGatewayEvent(event))
    .sort(sortByUpdatedDescending);
}

export async function getEventHistory() {
  if (apiConfig.useMockApi) {
    const { eventHistory } = await getMockData();
    return withMock(() => eventHistory);
  }

  const payload = await requestJson("/events");
  return unwrapItems(payload)
    .map((event) => mapGatewayEvent(event))
    .sort(sortByOccurredDescending);
}

export async function getDeviceStatus() {
  if (apiConfig.useMockApi) {
    const { devices } = await getMockData();
    return withMock(() => devices);
  }

  const payload = await requestJson("/devices");
  return unwrapItems(payload).map((device) => mapGatewayDevice(device));
}

export async function getLiveStreams() {
  if (apiConfig.useMockApi) {
    const { liveStreams } = await getMockData();
    return withMock(() => liveStreams);
  }

  const payload = await requestJson("/devices");
  return unwrapItems(payload)
    .map((device) => mapGatewayDevice(device))
    .map((device) => mapDeviceToStream(device));
}
