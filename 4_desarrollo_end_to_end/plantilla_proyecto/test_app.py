from app import app


def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_analyze_ok():
    client = app.test_client()
    response = client.post("/analyze", json={"text": "hola mundo esto es una prueba de resumen con suficientes palabras para truncar"})
    assert response.status_code == 200
    body = response.get_json()
    assert "summary" in body


def test_analyze_missing_text():
    client = app.test_client()
    response = client.post("/analyze", json={})
    assert response.status_code == 400
