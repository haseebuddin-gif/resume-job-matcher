"""API tests. Run: python -m pytest tests  (or: python tests/test_api.py)"""

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import api.main as api_main  # noqa: E402


def _client(tmp_custom: Path) -> TestClient:
    api_main.CUSTOM_JOBS = tmp_custom  # keep test jobs out of data/
    api_main.engine.invalidate()
    return TestClient(api_main.app)


def test_api_end_to_end(tmp_path: Path = None):
    tmp_path = tmp_path or Path(ROOT / ".cache")
    tmp_path.mkdir(exist_ok=True)
    custom = tmp_path / "custom_jobs_test.json"
    custom.unlink(missing_ok=True)
    c = _client(custom)

    cfg = c.get("/api/config").json()
    assert cfg["samples"] and cfg["models"]

    r = c.post("/api/analyze", data={"sample_name": "data_scientist.txt", "top_k": "5"})
    assert r.status_code == 200, r.text
    body = r.json()
    # hand-labelled relevant jobs for this resume (data/eval/annotations.json)
    assert {m["job_id"] for m in body["matches"][:3]} == {"J001", "J002", "J003"}
    assert 0 <= body["quality"]["score"] <= 100
    assert body["recommendations"] and body["comparison"]["rows"]

    resume = body["profile"]["raw_text"]
    ex = c.post("/api/explain", json={"resume_text": resume, "job_id": "J001"}).json()
    assert ex["evidence"] and "similarity" in ex["evidence"][0]

    up = c.post("/api/analyze", files={"file": ("cv.txt", io.BytesIO(resume.encode()), "text/plain")},
                data={"method": "tfidf"})
    assert up.status_code == 200 and up.json()["settings"]["method"] == "tfidf"

    bad = c.post("/api/analyze", files={"file": ("cv.exe", io.BytesIO(b"x" * 100), "application/octet-stream")})
    assert bad.status_code == 400

    jd = ("Requirements:\n- Python, PyTorch and NLP experience.\n- 1+ years of experience.\n"
          "Nice to have:\n- Docker and FastAPI.")
    cm = c.post("/api/match-custom", json={"resume_text": resume, "title": "NLP Intern", "description": jd})
    assert cm.status_code == 200, cm.text
    assert "Python" in cm.json()["match"]["gap"]["matched_required"]

    added = c.post("/api/jobs", json={"title": "ML Intern", "company": "Test Co", "description": jd})
    assert added.status_code == 201, added.text
    jid = added.json()["job_id"]
    assert any(j["job_id"] == jid for j in c.get("/api/jobs").json()["jobs"])
    assert c.delete(f"/api/jobs/{jid}").status_code == 204
    assert c.delete("/api/jobs/J001").status_code == 400
    custom.unlink(missing_ok=True)


if __name__ == "__main__":
    test_api_end_to_end()
    print("PASS test_api_end_to_end")
