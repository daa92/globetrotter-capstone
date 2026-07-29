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
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
