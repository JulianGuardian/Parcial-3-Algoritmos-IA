from fastapi import APIRouter

from app.api.v1 import conversations, disruptions

router = APIRouter()
router.include_router(disruptions.router)
router.include_router(conversations.router)
