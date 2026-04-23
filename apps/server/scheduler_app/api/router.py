from fastapi import APIRouter

from scheduler_app.api.routes import auth, events, integrations, polls, stats, workspaces


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(polls.router, tags=["polls"])
api_router.include_router(integrations.router, tags=["integrations"])
api_router.include_router(stats.router, prefix="/workspaces", tags=["stats"])
