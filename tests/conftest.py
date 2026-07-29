"""
tests/conftest.py

Points storage at a throwaway temp directory for every test run, so tests
never touch (or depend on) real data/*.json files.
"""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app import create_app, storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Redirect every storage path constant at a fresh temp directory.
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    monkeypatch.setattr(storage, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(storage, "USERS_FILE", str(data_dir / "users.json"))
    monkeypatch.setattr(storage, "ITINERARIES_FILE", str(data_dir / "itineraries.json"))
    monkeypatch.setattr(storage, "DESTINATIONS_FILE", str(data_dir / "destinations.json"))
    monkeypatch.setattr(storage, "PLACES_FILE", str(data_dir / "places.json"))
    monkeypatch.setattr(storage, "FEEDBACK_FILE", str(data_dir / "feedback.json"))
    monkeypatch.setattr(storage, "OUTBOX_FILE", str(data_dir / "outbox.json"))
    monkeypatch.setattr(storage, "ACTIVITY_FILE", str(data_dir / "activity.json"))
    monkeypatch.setattr(storage, "REFERRALS_FILE", str(data_dir / "referrals.json"))
    monkeypatch.setattr(storage, "PAYOUTS_FILE", str(data_dir / "payouts.json"))
    monkeypatch.setattr(storage, "NOTIFICATIONS_FILE", str(data_dir / "notifications.json"))

    seed = [
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
        }
    ]
    (data_dir / "destinations.json").write_text(json.dumps(seed))

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    shutil.rmtree(tmp_path, ignore_errors=True)
