"""Standard error envelope (no stack traces in JSON)."""

import pytest
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import RequestLoggingMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def error_app():
    application = FastAPI()

    @application.get("/boom")
    async def boom():
        raise RuntimeError("_test_internal_error_marker")

    @application.get("/item/{item_id}")
    async def item(item_id: int):
        return {"item_id": item_id}

    register_exception_handlers(application)
    application.add_middleware(RequestLoggingMiddleware)

    # ServerErrorMiddleware always re-raises after sending the 500 body so servers/tests can log it;
    # use raise_server_exceptions=False to assert on the JSON response.
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client


def _assert_error_envelope(data: object) -> dict:
    assert isinstance(data, dict)
    assert "error" in data
    err = data["error"]
    assert isinstance(err, dict)
    assert "code" in err and "message" in err
    return err


def test_404_error_format_and_no_stack(error_app: TestClient):
    response = error_app.get("/does-not-exist-xyz")
    assert response.status_code == 404
    body = response.json()
    err = _assert_error_envelope(body)
    assert err["code"] == "not_found"
    assert "traceback" not in response.text.lower()
    assert "_test_internal" not in response.text.lower()
    assert response.headers.get("X-Request-ID")


def test_422_validation_error_format(error_app: TestClient):
    response = error_app.get("/item/not-an-int")
    assert response.status_code == 422
    body = response.json()
    err = _assert_error_envelope(body)
    assert err["code"] == "validation_error"
    assert err["message"] == "Request validation failed"
    assert err.get("details") is not None
    assert "traceback" not in response.text.lower()


def test_500_internal_error_hides_details(error_app: TestClient):
    response = error_app.get("/boom")
    assert response.status_code == 500
    body = response.json()
    err = _assert_error_envelope(body)
    assert err["code"] == "internal_error"
    assert err["message"] == "An unexpected error occurred"
    assert "_test_internal_error_marker" not in response.text
    assert "traceback" not in response.text.lower()
    assert err.get("request_id")
