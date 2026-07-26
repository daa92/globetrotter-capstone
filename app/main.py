"""
app/main.py

Entry point. Run with:
    uvicorn app.main:app --reload --port 8000
or simply:
    python -m app.main
"""
import uvicorn

from app import create_app
from app.config import settings

app = create_app()

if __name__ == "__main__":
<<<<<<< HEAD
    port = int(os.environ.get("PORT", 5000))
    x = 1
    y = 2
    z = 1 + 2
    # Enable debug mode only when explicitly requested (e.g. FLASK_DEBUG=1).
    # Never enable debug in production – it exposes an interactive debugger.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
=======
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
>>>>>>> f25cd6e (Phase1: monolith; MFA, encryption and part of the backend completed.)
