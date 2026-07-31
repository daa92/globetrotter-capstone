"""
testing/challenges/prove_no_isolation_challenge.py

Slide claims:
  - "Failure: A single bug can crash the entire application. No isolation
    between services."
  - "Scalability: You can only scale vertically... Horizontal scaling is
    impossible."

REQUIRES the server running with SIMULATION_MODE=true in its .env (the
/debug/challenges/* endpoints only exist then — see app/__init__.py).

This fires enough concurrent, deliberately BLOCKING requests (real
time.sleep(), not await asyncio.sleep()) to saturate FastAPI's shared
thread pool, then measures how long a totally unrelated endpoint
(/health — not even a business feature, just a liveness probe) takes to
respond while that's happening.

In a real microservices split, a slow/broken Recommendations service
would never make a User service's health check slower — they're
different processes with independent resources. Here, everything shares
one process and one thread pool, so it does. That's "no isolation
between services," measured rather than asserted.

Usage:
    python testing/challenges/prove_no_isolation_challenge.py --host http://localhost:8000
"""
import argparse
import concurrent.futures
import time

import httpx


def _blocking_call(client: httpx.Client, host: str, seconds: float) -> float:
    start = time.perf_counter()
    client.get(f"{host}/debug/challenges/blocking-call", params={"seconds": seconds}, timeout=seconds + 10)
    return time.perf_counter() - start


def _health_check(client: httpx.Client, host: str) -> float:
    start = time.perf_counter()
    client.get(f"{host}/health", timeout=30)
    return time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description="Prove the monolith has no isolation between 'services'")
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument(
        "--saturating-requests", type=int, default=45,
        help="Concurrent blocking calls to fire — should exceed the shared thread pool's capacity",
    )
    parser.add_argument("--block-seconds", type=float, default=4.0)
    args = parser.parse_args()

    with httpx.Client() as client:
        try:
            baseline = _health_check(client, args.host)
        except httpx.HTTPStatusError:
            print("Could not reach /health at all — is the server running?")
            return
        print(f"Baseline /health latency (no load): {baseline:.3f}s")

        # Confirm the debug endpoints are actually live before going further —
        # a clear, honest failure if SIMULATION_MODE isn't on, instead of a
        # confusing pile of connection errors.
        probe = client.get(f"{args.host}/debug/challenges/blocking-call", params={"seconds": 0})
        if probe.status_code == 404:
            print("\n/debug/challenges/blocking-call returned 404 — the server isn't running with "
                  "SIMULATION_MODE=true. Set it in .env and restart the server, then re-run this script.")
            return

        print(f"\nFiring {args.saturating_requests} concurrent blocking calls "
              f"({args.block_seconds}s each) to saturate the shared thread pool...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.saturating_requests + 5) as pool:
            blocking_futures = [
                pool.submit(_blocking_call, client, args.host, args.block_seconds)
                for _ in range(args.saturating_requests)
            ]
            time.sleep(0.3)  # give the blocking calls a head start to actually occupy the pool
            health_future = pool.submit(_health_check, client, args.host)

            health_latency = health_future.result()
            [f.result() for f in blocking_futures]

    print(f"\n/health latency WHILE the thread pool was saturated: {health_latency:.3f}s")
    if health_latency > baseline * 3:
        print(f"[FAIL] /health -- a totally unrelated liveness-check endpoint -- was "
              f"{health_latency/baseline:.1f}x slower purely because of unrelated blocking\n"
              f"work happening elsewhere in the SAME process. This is 'no isolation between\n"
              f"services': in a real microservice split, the Recommendations service jamming up\n"
              f"would never touch the User service's health check.")
    else:
        print("(Not much slowdown observed this run -- try raising --saturating-requests; "
              "the shared thread pool's default capacity varies by environment.)")


if __name__ == "__main__":
    main()
