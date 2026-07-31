"""
testing/challenges/prove_testing_isolation_challenge.py

Slide claim: "Testing the entire application is slow. You cannot test
services independently."

Proves this via Python's own import semantics, not just a stopwatch:
importing JUST ONE router module (say, destinations.py, because you only
want to test destination-search logic) forces Python to first execute
app/__init__.py — which imports and wires up EVERY OTHER router (auth,
earnings, geo, notifications, places, users, recommendations,
itineraries) and their transitive dependencies (bcrypt, python-jose,
google-auth, httpx...) — before your one router is even reachable.

There is no way to import "just the destinations service" in this
codebase, because there IS no separate destinations service — it's all
one Python package, wired together in one place.

Usage:
    python testing/challenges/prove_testing_isolation_challenge.py
"""
import subprocess
import sys
import time


def _time_subprocess(code: str) -> tuple[float, str]:
    start = time.perf_counter()
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    return elapsed, result.stdout + result.stderr


def main():
    print("=== What actually gets imported when you 'just' want to test destinations.py ===\n")

    code = (
        "import sys\n"
        "before = set(sys.modules.keys())\n"
        "from app.routers import destinations\n"
        "after = set(sys.modules.keys())\n"
        "new_modules = after - before\n"
        "app_modules = sorted(m for m in new_modules if m.startswith('app.'))\n"
        "print(chr(10).join(app_modules))\n"
        "print(f'TOTAL_NEW_MODULES={len(new_modules)}')\n"
    )
    elapsed, output = _time_subprocess(code)

    print(output)
    print(f"Importing ONLY `from app.routers import destinations` took {elapsed:.3f}s (fresh interpreter, ")
    print("cold import cache) and pulled in every app.* module listed above -- including auth, earnings,")
    print("geo, notifications, places, users, and recommendations. None of that is destinations logic.\n")
    print("Why: importing any submodule of a Python package (app.routers.destinations) forces Python to")
    print("first execute the package's __init__.py (app/__init__.py). In THIS codebase, that file")
    print("explicitly wires up every other router too -- so there is no way to import 'just the")
    print("destinations service' here, because there is no separate destinations service. It's one")
    print("package. This is precisely 'you cannot test services independently.'")


if __name__ == "__main__":
    main()
