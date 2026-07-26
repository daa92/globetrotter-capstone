"""
testing/simulation/locustfile.py

Robustness & responsiveness simulation for GT.

This file is intentionally NOT imported by any app code and is NOT
copied into the production Docker image (see Dockerfile vs Dockerfile.dev,
and .dockerignore). It exists purely so you can point real, concurrent,
scripted traffic at a running instance and watch how it behaves:
response times, error rates under load, JSON-file storage contention,
JWT overhead, etc.

Usage (local, against the dev server on :8000):
    pip install -r requirements-dev.txt
    locust -f testing/simulation/locustfile.py --host http://localhost:8000
    # then open http://localhost:8089 to configure users/spawn-rate and start

Usage (via Docker, isolated from the main service):
    docker compose --profile simulation up locust
    # then open http://localhost:8089

Each simulated "user" registers once, logs in, then repeatedly searches
destinations, requests recommendations, and creates itineraries — a
rough approximation of real usage patterns, weighted toward the reads
(search/recommend) that a real recommendation engine needs to stay fast
under.
"""
import random
import uuid

from locust import HttpUser, between, task


class GTUser(HttpUser):
    wait_time = between(1, 3)  # seconds between simulated actions, mimics real think-time

    def on_start(self):
        self.username = f"sim_{uuid.uuid4().hex[:10]}"
        self.password = "SimPass123"
        self.client.post(
            "/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@example.com",
                "password": self.password,
                "preferences": random.sample(
                    ["beach", "hiking", "culture", "wildlife", "nightlife", "history"], k=2
                ),
            },
        )
        resp = self.client.post("/auth/login", json={"username": self.username, "password": self.password})
        self.token = resp.json().get("access_token")

    @property
    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def search_destinations(self):
        self.client.get("/destinations", params={"tag": random.choice(["beach", "hiking", "culture"])})

    @task(4)
    def get_recommendations(self):
        self.client.get("/recommendations", headers=self._auth_headers, name="/recommendations")

    @task(2)
    def create_itinerary(self):
        self.client.post(
            "/itineraries",
            headers=self._auth_headers,
            json={
                "title": "Simulated Trip",
                "destinations": ["limbe-botanic-beach"],
                "start_date": "2026-08-01",
                "end_date": "2026-08-07",
            },
            name="/itineraries [POST]",
        )

    @task(1)
    def list_itineraries(self):
        self.client.get("/itineraries", headers=self._auth_headers, name="/itineraries [GET]")

    @task(1)
    def submit_feedback(self):
        self.client.post(
            "/feedback",
            headers=self._auth_headers,
            json={"category": "suggestion", "message": "Simulated load-test feedback entry.", "rating": 4},
        )
