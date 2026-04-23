"""FastAPI command-center app for uploaded radar violations."""

import json
import os
import shutil
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


REPO_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = REPO_ROOT / "datasets" / "command-center" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="5G Akilli Yol Guvenligi - Komuta Merkezi")
app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

html_dashboard = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>5G KOMUTA MERKEZI - TEKNOFEST 2026</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; text-align: center; border-bottom: 2px solid #30363d; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); border-color: #8b949e; }
        .card img { width: 100%; height: 200px; object-fit: cover; border-bottom: 1px solid #30363d; }
        .info { padding: 15px; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; margin-bottom: 5px; }
        .badge-danger { background-color: #da3633; color: white; }
        .meta { font-size: 13px; color: #8b949e; margin-top: 10px; }
        .stat-box { background: #21262d; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>5G AKILLI YOL GUVENLIGI - MERKEZ</h1>

    <div class="stat-box">
        <h3>CANLI IHLAL AKISI (5G STREAM)</h3>
        <p>Sistem Durumu: <span style="color:#3fb950">ONLINE</span> | Bagli Araclar: 1</p>
    </div>

    <div class="grid" id="violations">
        {% for v in violations %}
        <div class="card">
            <img src="/static/{{ v.image_path }}" alt="Kanit Fotografi">
            <div class="info">
                <span class="badge badge-danger">HIZ IHLALI</span>
                <h3 style="margin: 5px 0">{{ v.speed }} km/s</h3>
                <p style="margin: 0">Limit: {{ v.limit }} km/s</p>
                <div class="meta">
                    <div>Arac ID: {{ v.vehicle_id }}</div>
                    <div>Lokasyon: {{ v.location }}</div>
                    <div>Zaman: {{ v.timestamp }}</div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    violations = []
    files = sorted(UPLOAD_DIR.iterdir(), reverse=True)

    for file_path in files:
        if file_path.suffix == ".json":
            try:
                with file_path.open("r", encoding="utf-8") as json_file:
                    data = json.load(json_file)
                    img_name = f"{data['record_id']}.jpg"
                    if (UPLOAD_DIR / img_name).exists():
                        violations.append(
                            {
                                "image_path": img_name,
                                "speed": data["measurements"]["final_speed"],
                                "limit": data["limit"],
                                "vehicle_id": data["vehicle_id"],
                                "location": data["location"],
                                "timestamp": data["timestamp"],
                            }
                        )
            except Exception as exc:
                print(f"Veri okuma hatasi: {exc}")

    from jinja2 import Template

    return Template(html_dashboard).render(violations=violations)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "command-center",
        "upload_dir": str(UPLOAD_DIR),
    }


@app.post("/api/violation")
async def upload_violation(
    request: Request,
    file: UploadFile = File(...),
    jsonData: str = Form(...),
):
    """Receive a radar violation payload from the field unit."""
    del request
    print(f"[5G] Veri alindi: {file.filename}")

    try:
        data = json.loads(jsonData)
        base_name = data["record_id"]
        img_path = UPLOAD_DIR / f"{base_name}.jpg"
        json_path = UPLOAD_DIR / f"{base_name}.json"

        with img_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with json_path.open("w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)

        return {"status": "success", "message": "Violation received at HQ", "id": base_name}
    except Exception as exc:
        print(f"HATA: {exc}")
        return {"status": "error", "message": str(exc)}


def main():
    """Run the command-center server."""
    host = os.getenv("COMMAND_CENTER_HOST", "0.0.0.0")
    port = int(os.getenv("COMMAND_CENTER_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
