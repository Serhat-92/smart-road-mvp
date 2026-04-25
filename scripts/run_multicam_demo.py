import subprocess, sys, concurrent.futures

CAMERAS = [
    {"camera_id": "cam-north-01", "video": "datasets/samples/bus-sample.mp4",
     "speed_limit": 1.0},
    {"camera_id": "cam-south-01", "video": "datasets/samples/bus-sample.mp4",
     "speed_limit": 1.0},
]

def run_camera(cam, token, gateway_url):
    cmd = [
        sys.executable, "scripts/run_local_mvp_demo.py",
        "--camera-id", cam["camera_id"],
        "--video", cam["video"],
        "--speed-limit", str(cam["speed_limit"]),
        "--gateway-url", gateway_url,
        "--api-token", token,
        "--radar-mock",
        "--allow-offline-gateway",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return cam["camera_id"], result.returncode, result.stdout[-500:]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8080")
    parser.add_argument("--gateway-user", default="admin")
    parser.add_argument("--gateway-password", default="admin123")
    args = parser.parse_args()

    # Token al
    import urllib.request, json, urllib.parse
    data = urllib.parse.urlencode(
        {"username": args.gateway_user, "password": args.gateway_password}
    ).encode()
    req = urllib.request.Request(
        f"{args.gateway_url}/auth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        resp = urllib.request.urlopen(req)
        token = json.loads(resp.read())["access_token"]
    except Exception:
        token = ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(CAMERAS)) as ex:
        futures = [ex.submit(run_camera, cam, token, args.gateway_url)
                   for cam in CAMERAS]
        for f in concurrent.futures.as_completed(futures):
            cam_id, code, out = f.result()
            print(f"\n[{cam_id}] exit={code}\n{out}")
