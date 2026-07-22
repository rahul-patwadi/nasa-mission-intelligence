"""FastAPI application entrypoint for NASA Mission Intelligence."""

from fastapi import FastAPI

from app.api.routes import missions, query
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Enterprise document intelligence system for NASA mission reports. "
        "Semantic search and natural-language querying over technical "
        "document repositories using RAG."
    ),
)

app.include_router(query.router)
app.include_router(missions.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status.

    Used by load balancers and deployment platforms (Render, Railway)
    to verify the service is alive before routing traffic.
    """
    return {"status": "healthy", "service": settings.app_name}
