from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .constants import ALLOWED_ORIGINS
from .logging_config import configure_logging, get_logger
from .routers import admin, chat, dashboard, health, tickets

configure_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Support Intelligence API", version="0.1.0")
    logger.info("Starting API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(tickets.router, prefix="/api/v1", tags=["Tickets"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

    return app


app = create_app()
