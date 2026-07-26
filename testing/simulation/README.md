# Simulation / Robustness Testing

Tools in this folder let you watch how GT behaves under load and under
malformed/adversarial input. They are development-only:

- **Not imported by any app code** — the app runs fine with this whole
  folder deleted.
- **Not in the production image** — `Dockerfile` only copies `app/` and
  `data/destinations.json`; `Dockerfile.dev` copies everything but is
  only used locally / in the `simulation` compose profile.
- **Gated behind an explicit action** — you must run these scripts (or
  the `simulation` Docker Compose profile) by hand; nothing auto-starts.

## `locustfile.py` — load / concurrency simulation

Simulates many concurrent users registering, searching, requesting
recommendations, and creating itineraries — the read-heavy pattern a
real recommendation feature needs to survive.

```bash
pip install -r requirements-dev.txt
locust -f testing/simulation/locustfile.py --host http://localhost:8000
# open http://localhost:8089, set user count + spawn rate, start
```

Or via Docker, isolated from your normal dev container:

```bash
docker compose --profile simulation up locust
```

Watch for: rising p95 latency as concurrent users increase, error rates
on `/recommendations` and `/itineraries` (POST), and how quickly the
JSON-file storage layer becomes the bottleneck — that bottleneck is
expected in Phase 1 and is exactly what Phase 2's database migration
fixes.

## `chaos_probe.py` — malformed/adversarial input probe

Fires oversized params, invalid payloads, unauthenticated requests at
protected routes, etc., and reports status codes + latency, so you can
eyeball whether validation is doing its job.

```bash
python testing/simulation/chaos_probe.py --host http://localhost:8000
```
