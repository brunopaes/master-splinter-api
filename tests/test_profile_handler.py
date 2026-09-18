from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

BOUNDARIES = [
    {"depth": 20, "duration": 3, "phase": "descend", "variation": 0.0},
    {"depth": 20, "duration": 5, "phase": "constant", "variation": 0.0},
    {"depth": 0, "duration": 2, "phase": "ascend", "variation": 0.0},
]


def test_profile_analysis_happy_path():
    response = client.post(
        "/profile-analysis",
        json={"boundaries": BOUNDARIES, "seed": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["seed"] == 1
    assert body["summary"]["max_depth"] == 20.0
    assert isinstance(body["stops"], list)
    assert isinstance(body["track"], list) and body["track"]
    assert len(body["final_tissues"]) == 16


def test_profile_analysis_rejects_empty_boundaries():
    response = client.post("/profile-analysis", json={"boundaries": []})

    assert response.status_code == 422
    assert "at least one segment" in response.json()["detail"]


def test_profile_analysis_rejects_unknown_gas():
    response = client.post(
        "/profile-analysis",
        json={"boundaries": BOUNDARIES, "gas": "trimix"},
    )

    assert response.status_code == 422
    assert "unknown gas" in response.json()["detail"]
