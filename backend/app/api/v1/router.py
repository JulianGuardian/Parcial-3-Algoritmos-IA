from fastapi import APIRouter

from app.api.v1.disruptions import router as disruptions_router

# Business endpoints (trip lookup, modifications, handoff) will be added here.
router = APIRouter()
router.include_router(disruptions_router)
