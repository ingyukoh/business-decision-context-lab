from fastapi.testclient import TestClient
from api import app
client = TestClient(app)


def test_schema_and_nonfinite_input():
    for x in ({"TV": True, "radio": 1, "newspaper": 2},
              {"TV": 1, "radio": 2},
              {"TV": -1, "radio": 2, "newspaper": 3},
              {"TV": "nan", "radio": 2, "newspaper": 3}):
        assert client.post("/predict", json=x).status_code == 422


def test_prediction_preserves_evidence_and_review():
    r = client.post("/predict", json={"TV": 80.2, "radio": 0, "newspaper": 9.2})
    assert r.status_code == 200
    assert r.json()["result"]["review_required"]
    assert r.json()["result"]["unit"] == "thousands of units"
    assert any(e["relation"] == "source" for e in r.json()["semantic_context"])


def test_recorded_generation_failure_is_not_hidden():
    x = client.get("/recorded-examples").json()
    wrong = next(c for c in x if c["row_id"] == 128 and c["context"])
    assert "million" in wrong["raw_model_output"]
    assert wrong["fallback_used"]
    assert "6.64 thousands of units" in wrong["displayed_summary"]


def test_ready_report():
    assert client.get("/health").status_code == 200
    assert client.get("/report").json()["test_n"] == 40
