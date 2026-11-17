import os

# Tests must never touch the developer's ./vigil.db: importing the app runs create_all on the default
# engine, so point that engine at a throwaway in-memory database BEFORE the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_ON_START"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models import models  # noqa: F401  (register tables)


@pytest.fixture
def session_factory():
    """Isolated in-memory SQLite database per test (one shared connection)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
