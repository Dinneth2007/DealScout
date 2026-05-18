"""End-to-end service test: POST /analyze -> poll -> download PDF.
Real pipeline, ~$0.20. Run on demand only: uv run pytest tests/integration -m integration
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from dealscout.service.api import app


@pytest.mark.integration
def test_full_service_flow() -> None:
    with TestClient(app) as client:
        r = client.post("/analyze", json={"input": "https://stripe.com"})
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        assert r.json()["status"] == "pending"

        deadline = time.time() + 360
        while time.time() < deadline:
            status = client.get(f"/jobs/{job_id}").json()["status"]
            if status == "complete":
                break
            if status == "failed":
                pytest.fail(client.get(f"/jobs/{job_id}").json().get("error_message"))
            time.sleep(5)
        else:
            pytest.fail("Job did not complete in 6 minutes")

        r = client.get(f"/memos/{job_id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert len(r.content) > 5000
