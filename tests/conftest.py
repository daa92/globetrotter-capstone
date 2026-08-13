"""
tests/conftest.py

Points storage at a fresh, isolated SQLite database for every test run,
so tests never touch (or depend on) the real TiDB database.

This replaces the old approach of monkeypatching storage.py's file-path
constants — now that storage.py is DB-backed, the equivalent isolation
is a throwaway SQLite engine, swapped in via monkeypatch on `db.engine`
(storage.py looks that up as `db.engine` at call time rather than
importing it by value, specifically so this works — see app/db.py).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import create_app, db, storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setattr(db, "engine", test_engine)
    db.metadata.create_all(test_engine)

    storage.append(
        storage.DESTINATIONS_FILE,
        {
            "id": "test-dest-1",
            "name": "Test Beach",
            "region": "South",
            "tags": ["beach", "relaxation"],
            "description": "A calm test beach with soft sand.",
            "image_url": "https://example.com/beach.jpg",
            "latitude": 2.95,
            "longitude": 9.91,
            "avg_cost_fcfa": 5000,
            "submitted_by": None,
        },
    )

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    test_engine.dispose()
