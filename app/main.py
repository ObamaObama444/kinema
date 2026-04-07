from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401
from app.api import auth_router, pages_router
from app.core.config import settings
from app.services.reminder_scheduler import reminder_scheduler

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

app.mount(
    "/assets",
    StaticFiles(directory=BASE_DIR.parent / "frontend" / "assets"),
    name="assets",
)

app.include_router(pages_router)
app.include_router(auth_router)


@app.on_event("startup")
def startup_event() -> None:
    reminder_scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    reminder_scheduler.stop()
