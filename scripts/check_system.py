"""System readiness check for the Smart Road MVP stack."""

from __future__ import annotations

import argparse
import json
import sys
from urllib import error, parse, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check gateway and AI service health.")
    parser.add_argument(
        "--gateway-url",
        default="http://127.0.0.1:8080",
        help="Gateway API base URL.",
    )
    parser.add_argument(
        "--inference-url",
        default=None,
        help="Optional AI inference base URL.",
    )
    parser.add_argument(
        "--gateway-user",
        default="admin",
        help="Gateway username.",
    )
    parser.add_argument(
        "--gateway-password",
        default="admin123",
        help="Gateway password.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def fetch_json(url: str, *, method: str = "GET", data: bytes | None = None, headers: dict | None = None, timeout: float = 5.0) -> dict:
    req = request.Request(url, data=data, headers=headers or {}, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def console_safe_symbol(symbol: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        symbol.encode(encoding)
    except UnicodeEncodeError:
        return {"\u2713": "OK", "\u2717": "X", "?": "?"}.get(symbol, symbol)
    return symbol


def print_status(symbol: str, label: str, message: str) -> None:
    symbol = console_safe_symbol(symbol)
    print(f"[{symbol}] {label:<18}: {message}")


def main() -> int:
    args = parse_args()
    warnings = 0
    failures = 0

    gateway_health = None
    try:
        gateway_health = fetch_json(
            f"{args.gateway_url.rstrip('/')}/health",
            timeout=args.timeout,
        )
        storage_backend = gateway_health["storage"]["backend"]
        print_status("✓", "Gateway API", f"OK (storage: {storage_backend})")
    except Exception as exc:
        failures += 1
        print_status("✗", "Gateway API", f"unreachable ({type(exc).__name__}: {exc})")

    try:
        auth_payload = parse.urlencode(
            {"username": args.gateway_user, "password": args.gateway_password}
        ).encode("ascii")
        auth_response = fetch_json(
            f"{args.gateway_url.rstrip('/')}/auth/token",
            method="POST",
            data=auth_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=args.timeout,
        )
        if auth_response.get("access_token"):
            print_status("✓", "Authentication", "OK")
        else:
            failures += 1
            print_status("✗", "Authentication", "token missing in response")
    except Exception as exc:
        failures += 1
        print_status("✗", "Authentication", f"failed ({type(exc).__name__}: {exc})")

    if gateway_health is not None:
        database = gateway_health.get("database", {})
        if database.get("connected"):
            print_status("✓", "PostgreSQL", "connected")
        else:
            failures += 1
            detail = database.get("last_error") or database.get("state") or "not connected"
            print_status("✗", "PostgreSQL", detail)

        redis_status = gateway_health.get("redis", {})
        if redis_status.get("connected"):
            print_status("✓", "Redis", "connected")
        else:
            warnings += 1
            detail = redis_status.get("last_error") or redis_status.get("state") or "not connected"
            print_status("✗", "Redis", f"not connected ({detail})")
    else:
        failures += 1
        print_status("✗", "PostgreSQL", "health response unavailable")
        warnings += 1
        print_status("✗", "Redis", "health response unavailable")

    if args.inference_url:
        try:
            inference_health = fetch_json(
                f"{args.inference_url.rstrip('/')}/health",
                timeout=args.timeout,
            )
            model_state = "loaded" if inference_health.get("model_loaded") else "not loaded"
            print_status("✓", "AI Inference", f"OK ({model_state})")
        except Exception as exc:
            warnings += 1
            print_status("✗", "AI Inference", f"unreachable ({type(exc).__name__}: {exc})")
    else:
        print_status("?", "AI Inference", "skipped (--inference-url not provided)")

    if failures:
        overall_status = "NOT READY"
    elif warnings:
        overall_status = "READY"
    else:
        overall_status = "READY"

    note_count = failures if failures else warnings
    note_label = "failure" if failures == 1 else "failures" if failures > 1 else "warning" if warnings == 1 else "warnings"
    if failures or warnings:
        print(f"\nSystem status: {overall_status} ({note_count} {note_label})")
    else:
        print(f"\nSystem status: {overall_status}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
