import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_app_imports_without_error():
    from app.main import app

    assert isinstance(app, FastAPI)


def test_lifespan_runs_on_testclient_context():
    """TestClient enters lifespan on open; validates startup path without binding a port."""
    from app.main import app

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200


def test_root_main_reexports_app_without_circular_import():
    import main as root_main

    assert isinstance(root_main.app, FastAPI)


def test_clean_interpreter_imports_no_circular_dependency():
    """Fresh process ensures import graph resolves (catches circular imports)."""
    code = (
        "import app.main; "
        "import main as root_main; "
        "assert root_main.app is app.main.app"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_uvicorn_process_starts_and_serves_health():
    """Real server bind smoke test (validates CLI / ASGI string resolution)."""
    port = 19987
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 15.0
    try:
        while time.monotonic() < deadline:
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{port}/api/v1/health", timeout=1.0
                )
                if response.status_code == 200:
                    assert response.json() == {"status": "ok"}
                    return
            except httpx.RequestError:
                time.sleep(0.15)
                if proc.poll() is not None:
                    break
        pytest.fail(
            f"uvicorn did not become ready in time. exit_code={proc.poll()}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
