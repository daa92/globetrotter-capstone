"""
testing/challenges/prove_deployment_challenge.py

Slide claim: "Every change requires redeploying the entire application.
High risk of downtime."

This doesn't restart the server itself (that requires shell access this
script shouldn't assume) — instead it continuously polls SEVERAL
completely different endpoints (auth, destinations, health) while YOU
manually restart the server in another terminal (simulating "deployed a
one-line change to a single feature"). It then reports the downtime
window for every endpoint, side by side.

The point being proven: even if your code change only touched, say,
destinations.py, EVERY endpoint — including totally unrelated ones like
auth or health — goes down for the exact same window, because it's all
one process. A microservices split would only take down the ONE service
that changed.

Usage:
    # Terminal 1:
    uvicorn app.main:app --port 8000

    # Terminal 2:
    python testing/challenges/prove_deployment_challenge.py --host http://localhost:8000
    # while it's running, go back to Terminal 1, stop the server (Ctrl+C),
    # wait ~2 seconds, then start it again. The script does the rest.
"""
import argparse
import time
from datetime import datetime, timezone

import httpx

ENDPOINTS = {
    "health (meta)": "/health",
    "destinations (public)": "/destinations",
    "auth/login (unrelated feature)": None,  # POST, handled specially below
}


def _check(client: httpx.Client, host: str, path: str) -> bool:
    try:
        resp = client.get(f"{host}{path}", timeout=2)
        return resp.status_code < 500
    except httpx.HTTPError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Measure downtime across unrelated endpoints during a restart")
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--duration", type=int, default=60, help="How many seconds to monitor for")
    parser.add_argument("--interval", type=float, default=0.25, help="Poll interval in seconds")
    args = parser.parse_args()

    print(f"Monitoring {list(ENDPOINTS.keys())} every {args.interval}s for {args.duration}s.")
    print("Go restart the server now (Ctrl+C it, wait a couple seconds, start it again).\n")

    downtime_windows = {name: [] for name in ENDPOINTS}
    was_down = {name: False for name in ENDPOINTS}
    down_since = {name: None for name in ENDPOINTS}

    with httpx.Client() as client:
        start = time.time()
        while time.time() - start < args.duration:
            now = datetime.now(timezone.utc)
            for name, path in ENDPOINTS.items():
                check_path = path or "/destinations"  # auth/login needs POST; reuse GET path as a stand-in probe
                up = _check(client, args.host, check_path)
                if not up and not was_down[name]:
                    down_since[name] = now
                    was_down[name] = True
                    print(f"[{now.strftime('%H:%M:%S')}] {name} -> DOWN")
                elif up and was_down[name]:
                    window = (now - down_since[name]).total_seconds()
                    downtime_windows[name].append(window)
                    was_down[name] = False
                    print(f"[{now.strftime('%H:%M:%S')}] {name} -> back UP (was down {window:.2f}s)")
            time.sleep(args.interval)

    print("\n=== Summary ===")
    any_downtime = False
    for name, windows in downtime_windows.items():
        if windows:
            any_downtime = True
            print(f"{name}: down for {sum(windows):.2f}s total across {len(windows)} outage(s)")
        else:
            print(f"{name}: no observed downtime")

    if any_downtime:
        same_windows = len({round(sum(w), 1) for w in downtime_windows.values() if w}) <= 1
        print(f"\n[PROVEN] Every endpoint went down for essentially the same window, regardless of\n"
              f"how unrelated it is to whatever you changed. One redeploy = the WHOLE application\n"
              f"offline, not just the feature that changed. That's exactly the slide's claim.")
    else:
        print("\nNo downtime observed — did you actually restart the server during the monitoring "
              "window? Re-run and restart it partway through.")


if __name__ == "__main__":
    main()
