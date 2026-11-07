from fastapi import APIRouter

from app.api.v1 import disruptions

router = APIRouter()
router.include_router(disruptions.router)
