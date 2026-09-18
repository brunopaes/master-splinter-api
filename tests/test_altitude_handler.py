from fastapi.testclient import TestClient

from api.main import app
from master_splinter.model.splinter_decompression import initialize_tissues

client = TestClient(app)

SURFACE_TISSUES = initialize_tissues()


def test_altitude_analysis_descent_is_always_safe():
    response = client.post(
        "/altitude-analysis",
        json={"tissues": SURFACE_TISSUES, "elevation_gain": -500.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["safe"] is True
    assert body["raw"]["safe"] is True
    assert body["gradient"]["safe"] is True


def test_altitude_analysis_rejects_wrong_tissue_count():
    response = client.post(
        "/altitude-analysis",
        json={"tissues": SURFACE_TISSUES[:15], "elevation_gain": 100.0},
    )

    assert response.status_code == 422
