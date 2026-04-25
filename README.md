# 5G Supported Smart Road Safety MVP

This repository is currently a local MVP for vehicle detection, simple tracking,
approximate speed estimation, violation event generation, and operator review.

It is not an enforcement-ready product. The current goal is to demonstrate a
working local flow:

1. Read a sample video.
2. Detect vehicles with YOLO.
3. Assign simple track IDs.
4. Estimate approximate visual speed.
5. Generate a speed violation event when a configured speed limit is exceeded.
6. Save an annotated evidence frame.
7. Send the event to the FastAPI gateway.
8. Show the event in the React operator dashboard.

## Current MVP Status

### Implemented

- Monorepo folder structure with `services`, `apps`, `shared`, `infra`, `datasets`,
  `notebooks`, and `tests`.
- FastAPI gateway service with `/health`, `/events`, `/devices`, and
  `/ingest/frame`.
- In-memory event, device, and frame-ingest repositories.
- PostgreSQL availability probe and fallback status reporting.
- Shared event contracts for detection events, fused vehicle events, and speed
  violation alerts.
- YOLO-based vehicle detection using the repository's existing detection logic.
- Local video-file processing with configurable frame sampling.
- Simple multi-object tracking using lightweight matching.
- Approximate computer-vision speed estimation from tracked movement.
- Speed violation event generation.
- Annotated evidence image generation under `datasets/evidence`.
- Event delivery from the inference pipeline to the gateway API.
- React + Vite operator dashboard connected to the gateway API.
- Dashboard polling for near-real-time event refresh.
- Local evidence image preview through the Vite dev server.
- Dockerfiles and `infra/docker-compose.yml` for local service startup.
- Integration tests for gateway, inference API, video pipeline, event contracts,
  evidence generation, and fallback behavior.
- PostgreSQL async persistence with SQLAlchemy and asyncpg.
- Redis pub/sub event queue with HTTP fallback.
- RTSP camera stream support with reconnect logic.
- License plate OCR with EasyOCR (lazy-load).
- WebSocket real-time event push to operator dashboard.
- JWT authentication (Bearer token) for all protected endpoints.
- Radar hardware integration (MockRadarSensor and RadarSensor).

### Simulated Or Approximate

- Radar data is simulated or manually supplied with `--radar-speed`; no real radar
  hardware is connected in the MVP flow.
- Speed estimation is approximate and based on image-space movement. It is useful
  for a demo, not for legal or calibrated enforcement.
- The live stream dashboard page is a placeholder.
- The command center app is a legacy/prototype upload receiver, not the main MVP
  event dashboard.

### Planned

- Add calibrated speed estimation and radar correction.
- Add event acknowledgement and operator workflow states.
- Improve Docker production images and deployment configuration.

## Architecture Summary

```text
Local video / RTSP camera
      |
      v
services/ai-inference
  YOLOv8 detection → tracking → speed estimation → plate OCR
      |
      v
speed.violation_alert event + evidence image
      |
  Redis pub/sub (HTTP fallback)
      |
      v
services/gateway-api
  JWT auth → PostgreSQL persistence → WebSocket broadcast
      |
      v
apps/operator-dashboard
  Real-time WebSocket feed + evidence image display
```

## Service List

### `services/gateway-api`

FastAPI backend for local MVP events and device metadata.

Working endpoints:

- `GET /health`
- `GET /events`
- `POST /events`
- `GET /devices`
- `POST /devices`
- `POST /ingest/frame`

Current storage is in memory. If PostgreSQL is unavailable, the service continues
running with the memory fallback.

### `services/ai-inference`

Vehicle inference service and reusable pipeline code.

Implemented capabilities:

- image/frame analysis endpoint
- local video analysis endpoint
- YOLO vehicle detection
- simple track IDs
- approximate speed estimation
- simulated radar fusion helpers
- speed violation event generation
- evidence frame saving
- optional publishing to the gateway API

Useful endpoints when running `service_api.py`:

- `GET /health`
- `POST /frame/analyze`
- `POST /frame/analyze/base64`
- `POST /video/analyze`
- `POST /radar/fuse`

### `apps/operator-dashboard`

React + Vite dashboard for local operator review.

Implemented pages:

- Active events
- Event history
- Device status
- Placeholder live stream view

The dashboard reads from the gateway API by default and refreshes events every few
seconds.

### `shared/event-contracts`

Shared JSON schemas and Python Pydantic models for:

- `detection.event`
- `fused.vehicle_event`
- `speed.violation_alert`

### `infra`

Local Docker Compose configuration for:

- PostgreSQL
- Redis
- gateway API
- AI inference service
- operator dashboard
- command center prototype as an optional `legacy` profile

### `scripts`

Local helper scripts. The main demo entrypoint is:

- `scripts/run_local_mvp_demo.py`

## Repository Layout

```text
apps/
  command-center/        Prototype/legacy violation upload UI
  operator-dashboard/    React dashboard for local MVP review
services/
  ai-inference/          Detection, tracking, speed, fusion, event generation
  gateway-api/           FastAPI event/device/ingest gateway
shared/
  event-contracts/       Shared JSON schemas and Python event models
  python/                Monorepo import helpers
infra/
  docker-compose.yml     Local service stack
datasets/
  samples/               Sample demo video files
  evidence/              Generated annotated evidence images
notebooks/               Future experiments
tests/
  integration/           Integration tests
src/                     Compatibility wrappers for older project entrypoints
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- Docker Desktop, optional but useful for Compose
- `yolov8n.pt` in the repository root, or network access so Ultralytics can fetch
  the model when using the default model name

## Local Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install dashboard dependencies:

```powershell
cd apps/operator-dashboard
npm install
cd ..\..
```

## Run The MVP Demo Locally

### 1. Start The Gateway API

Open a PowerShell terminal from the repository root:

```powershell
$env:GATEWAY_API_HOST='127.0.0.1'
$env:GATEWAY_API_PORT='8080'
$env:POSTGRES_ENABLED='false'
python services/gateway-api/main.py
```

#### PostgreSQL ile başlatmak için (opsiyonel):

```powershell
copy infra\.env.example infra\.env
$env:POSTGRES_ENABLED='true'
$env:POSTGRES_HOST='127.0.0.1'
$env:POSTGRES_USER='postgres'
$env:POSTGRES_PASSWORD='postgres'
$env:POSTGRES_DB='gateway_api'
python services/gateway-api/main.py
```

Check it:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
```

### 2. Start The Dashboard

Open a second PowerShell terminal:

```powershell
cd apps/operator-dashboard
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

### 3. Run The Video-To-Event Demo

Open a third PowerShell terminal from the repository root:

```powershell
python scripts/run_local_mvp_demo.py --gateway-user admin --gateway-password admin123
```

The default demo uses:

- video: `datasets/samples/bus-sample.mp4`
- gateway: `http://127.0.0.1:8080`
- speed limit: `1.0 km/h`

The speed limit is intentionally low so the short sample video creates a visible
event during local testing.

> **Not:** Demo artık JWT token gerektirmektedir. `--gateway-user` ve
> `--gateway-password` parametreleri ile token otomatik olarak alınır.
> Alternatif olarak `--api-token` ile doğrudan token verilebilir.

Check stored events (JWT token gerekli):

```powershell
# Önce token al
$token = (Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/auth/token `
  -Body @{username="admin"; password="admin123"}).access_token

# Eventleri listele
Invoke-RestMethod -Uri http://127.0.0.1:8080/events `
  -Headers @{Authorization="Bearer $token"}
```

Evidence images are written to:

```text
datasets/evidence/
```

Useful demo options:

```powershell
python scripts/run_local_mvp_demo.py --speed-limit 70 --max-frames 20 --gateway-user admin --gateway-password admin123
python scripts/run_local_mvp_demo.py --radar-speed 82.5 --gateway-user admin --gateway-password admin123
python scripts/run_local_mvp_demo.py --radar-mock --video datasets/samples/bus-sample.mp4 --gateway-user admin --gateway-password admin123
python scripts/run_local_mvp_demo.py --allow-offline-gateway
```

## Docker Compose ile Tam Sistem

### Gereksinimler
- Docker Desktop çalışıyor olmalı
- yolov8n.pt dosyası repo kökünde olmalı

### Başlatma (tek komut)
```powershell
copy infra\.env.example infra\.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build
```

### Erişim
- Operatör Panosu : http://localhost:5173
- Gateway API     : http://localhost:8080/health
- AI Inference    : http://localhost:8090/health

Not: İlk build easyocr modeli indireceğinden 5-10 dakika sürebilir.

### Demo Komutu (Docker dışında, lokal)
```powershell
$env:PYTHONPATH="services\ai-inference\src;shared\event-contracts\python;shared\python"
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8080/auth/token" `
  -Method Post -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=admin123"
$token = $response.access_token
python scripts/run_local_mvp_demo.py `
  --radar-mock `
  --video datasets\samples\bus-sample.mp4 `
  --api-token $token
```

### Durdurma
```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

## Run Tests

Run all current integration tests:

```powershell
python -m unittest discover -s tests/integration
```

Run a quick Python compile check:

```powershell
python -m compileall services/gateway-api services/ai-inference shared/event-contracts/python scripts tests/integration
```

Build the dashboard:

```powershell
cd apps/operator-dashboard
npm run build
```

## Güvenlik Notu

> **Uyarı:** Varsayılan operatör giriş bilgileri `admin` / `admin123` olarak
> ayarlanmıştır. Bu değerler yalnızca geliştirme ve demo amaçlıdır.
> Production ortamında aşağıdaki environment değişkenlerini mutlaka değiştirin:
>
> ```
> GATEWAY_ADMIN_USER=<güvenli_kullanıcı_adı>
> GATEWAY_ADMIN_PASSWORD=<güçlü_şifre>
> GATEWAY_JWT_SECRET_KEY=<rastgele_uzun_anahtar>
> ```

## Known Limitations

- Speed values are approximate and not calibrated.
- Evidence images are served locally by the Vite dev/preview server for demo use.
- Docker images are for local development, not hardened production deployment.
- Error handling is suitable for local MVP testing, not full production operations.

## What To Demo

For the cleanest local demo:

1. Start `services/gateway-api`.
2. Start `apps/operator-dashboard`.
3. Run `python scripts/run_local_mvp_demo.py`.
4. Refresh or wait for the dashboard event polling.
5. Open the generated speed violation event.
6. Confirm the event fields and evidence image path are visible.

This is the working MVP path today.
