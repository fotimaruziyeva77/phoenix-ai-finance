"""
Application use-cases. Routers should call services; services call repositories
(or integrations) and enforce business rules.

Health is synthetic (no persistence); future DB checks belong behind a
repository injected into this service.
"""


async def get_public_health() -> dict[str, str]:
    """Liveness payload for load balancers and ops."""
    return {"status": "ok"}
