"""Run inside the backend container: DB (async), Redis TCP, MinIO HTTP."""

from __future__ import annotations

import asyncio
import socket
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx
from sqlalchemy import text

from app.core.db import dispose_engine, get_engine


async def main() -> int:
    s = socket.create_connection(("redis", 6379), timeout=5)
    s.close()
    print("redis_reachable: tcp_ok")

    engine = get_engine()
    try:
        async with engine.connect() as conn:
            one = (await conn.execute(text("SELECT 1"))).scalar_one()
            assert one == 1
        print("postgres_via_sqlalchemy: select_1_ok")
    finally:
        await dispose_engine()

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get("http://minio:9000/minio/health/live")
        response.raise_for_status()
    print("minio_reachable: health_live_ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
