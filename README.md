# BotForge AI

## Python runtime

Use **Python 3.12** everywhere (local host, CI, and the API Docker image). The repo pins this via:

- **`.python-version`** — `pyenv`, `asdf`, and similar tools pick 3.12 automatically
- **`pyproject.toml`** — Ruff `target-version = "py312"` (syntax / lint baseline matches the runtime)
- **`Dockerfile`** — `python:3.12-slim-bookworm`
- **GitHub Actions** — `python-version: "3.12"` plus `scripts/check_python_version.py` in workflows

Quick check:

```bash
python scripts/check_python_version.py
```

## Local backend (host)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
```

Copy and adjust `.env` (see `docs/deployment/`). Run the API with `python main.py` or `uvicorn` as in `docs/deployment/RUNBOOK.md`.

## Docker stack

```bash
docker compose up --build
```

## Docs

- **Deployment / tiers:** [docs/deployment/ENVIRONMENTS.md](docs/deployment/ENVIRONMENTS.md)
- **CI & integration tests:** [docs/qa/CI_INTEGRATION.md](docs/qa/CI_INTEGRATION.md)
- **MVP release:** [docs/release/README.md](docs/release/README.md)
