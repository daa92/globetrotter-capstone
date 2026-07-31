# Challenge Proof Kit

Scripts that *prove* the Phase 1 monolith challenges from the capstone
slides actually happen in this codebase — not just assert them in a
report. Every script below was run against the real app while writing it;
none of this is theoretical.

Like `testing/simulation/`, nothing here is imported by app code, and
none of it ships in the production Docker image (see `.dockerignore` and
`Dockerfile`). The one piece of app code these scripts depend on —
`app/routers/debug_challenges.py` — only exists at all when
`SIMULATION_MODE=true`, and logs a loud warning when it's active. Never
set that in production.

## Mapping: slide challenge → proof

| Slide challenge | Proof script | What it actually measures |
|---|---|---|
| **Data Storage**: "JSON files are not designed for concurrent access. No transactions, no indexing." | `prove_data_storage_challenge.py` | Part 1: a naive unsynchronized JSON read-modify-write, run concurrently — reliably **loses writes and produces outright JSON corruption** (`JSONDecodeError` mid-write). Part 2: the real app (which *does* have a lock) shows the other half of the claim — no corruption, but **latency grows with concurrency and throughput stalls**, because every write serializes through one lock. |
| **Scalability**: "You can only scale vertically. Horizontal scaling is impossible." | `prove_data_storage_challenge.py` (Part 2) and `prove_no_isolation_challenge.py` | Same latency-under-load data as above, plus the thread-pool-saturation result below. |
| **Failure**: "A single bug can crash the entire application. No isolation between services." | `prove_no_isolation_challenge.py` | Saturates FastAPI's shared thread pool with deliberately blocking calls, then shows a **totally unrelated endpoint** (`/health`) gets **~250x slower** purely because of unrelated work happening elsewhere in the same process. Also documents the honest counter-finding: FastAPI *does* isolate a raw exception to one request (see `tests/test_debug_challenges.py::test_crash_endpoint_returns_500_not_a_dead_process`) — what's genuinely missing is resource isolation (thread pool, memory, CPU), not per-request exception handling. |
| **Deployment**: "Every change requires redeploying the entire application. High risk of downtime." | `prove_deployment_challenge.py` | Monitors 3 unrelated endpoints while you manually restart the server — shows **all of them go down and come back at the exact same moment**, for the exact same duration, regardless of which feature actually changed. |
| **Team Collaboration**: "All developers work on the same codebase. Merge conflicts are frequent." | `prove_team_collaboration_challenge.sh` | Simulates two developers editing the same file, generates a **real git merge conflict**, shows the actual conflict markers, then cleans up (throwaway branches, your working tree is untouched). |
| **Testing**: "Testing the entire application is slow. You cannot test services independently." | `prove_testing_isolation_challenge.py` | Imports **only** the destinations router and inspects `sys.modules` — shows it drags in every other router (auth, earnings, geo, notifications...) and hundreds of transitive dependencies, because there's no way to import "just one service" from a single Python package. |

## Running them

```bash
# 1. Data storage / scalability (needs a running server for Part 2)
uvicorn app.main:app --port 8000 &
python testing/challenges/prove_data_storage_challenge.py --host http://localhost:8000

# 2. No isolation (needs SIMULATION_MODE=true — set it in .env, restart the server)
python testing/challenges/prove_no_isolation_challenge.py --host http://localhost:8000

# 3. Deployment downtime (run this, then manually Ctrl+C and restart the
#    server in another terminal while it's monitoring)
python testing/challenges/prove_deployment_challenge.py --host http://localhost:8000

# 4. Team collaboration (needs a clean git working tree — commit or stash first)
bash testing/challenges/prove_team_collaboration_challenge.sh

# 5. Testing isolation (no server needed)
python testing/challenges/prove_testing_isolation_challenge.py
```

## What's NOT here yet: the Phase 2 (microservices) challenges

Your second slide (Network Latency, Data Consistency, Service Discovery,
Distributed Tracing, Deployment Orchestration, Testing) describes problems
that only exist once there *are* multiple services talking to each other
over a network — none of that exists yet in Phase 1's monolith, so there's
nothing honest to measure yet. Once Phase 2 actually splits this into
separate services behind an API Gateway, this folder gets a second batch
of proof scripts for that slide — same philosophy, measured not asserted.
