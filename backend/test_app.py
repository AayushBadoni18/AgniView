from agniview.api import create_app


class EmptyRepository:
    pass


def test_health_endpoint():
    response = create_app(EmptyRepository()).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "backend", "database": "ok"}
