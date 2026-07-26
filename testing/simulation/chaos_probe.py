"""
testing/simulation/chaos_probe.py

A tiny, deliberately dumb fault-injection script — the "poke it and see
what happens" tool for Phase 1. It fires deliberately malformed,
oversized, concurrent, and malicious-shaped requests at a running
instance and reports how the API responded (status code + latency),
so you can see where validation is weak before real users find it.

This is NOT a security scanner and NOT a substitute for the resilience
work planned for Phase 4 (circuit breakers, retries, etc.) — it's a
lightweight local sanity check you run by hand during development.

Usage:
    python testing/simulation/chaos_probe.py --host http://localhost:8000
"""
import argparse
import concurrent.futures
import time

import httpx


SCENARIOS = [
    ("GET", "/health", None, "baseline health check"),
    ("GET", "/destinations", None, "plain search"),
    ("GET", "/destinations?tag=" + "x" * 5000, None, "oversized query param"),
    ("POST", "/auth/register", {"username": "a", "email": "not-an-email", "password": "123"}, "invalid registration payload"),
    ("POST", "/auth/login", {"username": "nobody", "password": "wrong"}, "login with unknown user"),
    ("GET", "/recommendations", None, "protected route with no auth header"),
    ("POST", "/itineraries", {"title": "", "destinations": [], "start_date": "not-a-date", "end_date": "2020-01-01"}, "malformed itinerary"),
]


def run_scenario(client: httpx.Client, method: str, path: str, payload, label: str) -> dict:
    start = time.perf_counter()
    try:
        resp = client.request(method, path, json=payload, timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"label": label, "status": resp.status_code, "ms": round(elapsed_ms, 1)}
    except httpx.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"label": label, "status": f"ERROR: {exc}", "ms": round(elapsed_ms, 1)}


def main():
    parser = argparse.ArgumentParser(description="GT robustness probe")
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=10, help="How many times to repeat all scenarios in parallel")
    args = parser.parse_args()

    with httpx.Client(base_url=args.host) as client:
        print(f"Probing {args.host} with {args.concurrency}x concurrency over {len(SCENARIOS)} scenarios...\n")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [
                pool.submit(run_scenario, client, method, path, payload, label)
                for _ in range(args.concurrency)
                for method, path, payload, label in SCENARIOS
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for r in sorted(results, key=lambda x: x["label"]):
        print(f"[{r['status']:>5}] {r['ms']:>7}ms  {r['label']}")


if __name__ == "__main__":
    main()
