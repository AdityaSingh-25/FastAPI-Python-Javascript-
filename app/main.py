from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db_models
from app.config import get_settings
from app.database import engine
from app.observability import configure_logging, observability_middleware
from app.routers import meta, products
from app.security import require_api_key

configure_logging()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite is the zero-config local/dev/test backend, so create tables on the
    # fly. Other backends (e.g. Postgres) are managed by Alembic migrations
    # (`alembic upgrade head`) and are intentionally left untouched here.
    if engine.url.get_backend_name() == "sqlite":
        db_models.Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        summary="Inventory and catalog management APIs for a SaaS product operations dashboard.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(observability_middleware)

    app.include_router(meta.router)
    app.include_router(products.router, dependencies=[Depends(require_api_key)])
    return app


app = create_app()
