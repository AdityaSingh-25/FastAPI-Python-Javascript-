import os

# Force an in-memory SQLite database for the test run before `app` (and the
# `app.database` module it imports) build their engine. Settings read DATABASE_URL
# via pydantic-settings, so setting it here takes precedence over any local .env
# and keeps the suite independent of the developer's real database.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db_models
from app.config import get_settings
from app.dependencies import get_db
from app.main import app
from app.observability import counters
from app.security import rate_limiter

# A single in-memory engine shared by every test, wired into the app via a
# dependency override. StaticPool keeps one connection so the in-memory schema
# persists across requests within a test.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_state():
    db_models.Base.metadata.drop_all(bind=engine)
    db_models.Base.metadata.create_all(bind=engine)
    rate_limiter.reset()
    counters.reset()
    yield
    # Drop any settings/limiter state a test mutated (e.g. via monkeypatched
    # env vars) so it cannot leak into the next test.
    get_settings.cache_clear()
    rate_limiter.reset()
