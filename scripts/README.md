# Local MVP Demo Runner

This folder contains small operational scripts for local development demos.

## Video-to-event demo

The demo processes the bundled sample video, runs YOLO vehicle detection,
assigns track IDs, estimates approximate computer-vision speed, saves annotated
evidence frames for violations, and sends `speed.violation_alert` events to the
gateway API.

The runner calls the AI inference pipeline directly in-process, so you only need
the gateway API running for event delivery. You do not need to start
`services/ai-inference/service_api.py` for this demo.

### 1. Start the gateway API

Open PowerShell from the repository root:

```powershell
$env:GATEWAY_API_HOST='127.0.0.1'
$env:GATEWAY_API_PORT='8080'
$env:POSTGRES_ENABLED='false'
python services/gateway-api/main.py
```

Keep that terminal open.

### 2. Run the demo

Open a second PowerShell terminal from the repository root:

```powershell
python scripts/run_local_mvp_demo.py
```

The default speed limit is intentionally low (`1.0 km/h`) so the short bundled
sample video generates at least one event during local testing.

### Useful options

```powershell
python scripts/run_local_mvp_demo.py --speed-limit 70 --max-frames 20
python scripts/run_local_mvp_demo.py --radar-speed 82.5
python scripts/run_local_mvp_demo.py --camera-id demo-cam-02 --sample-rate-fps 5
```

### Check results

Gateway events:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/events
```

Evidence images are saved under:

```text
datasets/evidence/
```
