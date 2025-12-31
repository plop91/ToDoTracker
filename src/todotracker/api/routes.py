"""API router aggregation."""

from fastapi import APIRouter

from todotracker.api.todos import router as todos_router
from todotracker.api.categories import router as categories_router
from todotracker.api.tags import router as tags_router
from todotracker.api.priorities import router as priorities_router
from todotracker.api.attachments import router as attachments_router

router = APIRouter(prefix="/api")

router.include_router(todos_router)
router.include_router(categories_router)
router.include_router(tags_router)
router.include_router(priorities_router)
router.include_router(attachments_router)
