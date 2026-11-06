from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: no auth, no external dependencies."""
    return {"status": "ok"}
