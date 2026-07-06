from fastapi import APIRouter

from app.api.v1.endpoints import admin, convert, feedback, health, maintenance, upload

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(convert.router)
api_router.include_router(feedback.router)
api_router.include_router(maintenance.router)
api_router.include_router(admin.router)
