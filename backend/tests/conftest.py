"""Tests run against a throwaway PostgreSQL database and MongoDB database, never the real ones."""
import os
import re
import sys
from pathlib import Path

import psycopg
import pytest
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

TEST_DB = "law_firm_pytest"
TEST_MONGO_DB = "law_firm_pytest_docs"


def base_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL is not set")


URL = base_url()
ADMIN_DSN = re.sub(r"^postgresql\+psycopg://", "postgresql://", URL)
ADMIN_DSN = ADMIN_DSN.rsplit("/", 1)[0] + "/postgres"
TEST_URL = URL.rsplit("/", 1)[0] + f"/{TEST_DB}"
os.environ["DATABASE_URL"] = TEST_URL
os.environ["MONGODB_DB"] = TEST_MONGO_DB
os.environ["DEBUG"] = "false"


def run_alembic_upgrade():
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")


@pytest.fixture(scope="session", autouse=True)
def databases():
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")
    run_alembic_upgrade()
    dsn = ADMIN_DSN.rsplit("/", 1)[0] + f"/{TEST_DB}"
    with psycopg.connect(dsn, autocommit=True) as conn:
        for name in ("sample_data.sql", "sample_activity.sql"):
            conn.execute((BACKEND.parent / "database" / name).read_text().encode())

    mongo = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=3000)
    mongo.drop_database(TEST_MONGO_DB)
    from mongo_migrations import m001_document_store
    m001_document_store.upgrade(mongo[TEST_MONGO_DB])

    yield

    from app.database import engine
    engine.dispose()
    mongo.drop_database(TEST_MONGO_DB)
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")


@pytest.fixture(scope="session")
def client(databases):
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def login(client, username, password):
    r = client.post("/api/v1/auth/login-json", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin", "admin123")


@pytest.fixture(scope="session")
def lawyer(client):
    """Ananya Rao. Lead on matter 2, not on matter 1."""
    return login(client, "lawyer1", "lawyer123")


@pytest.fixture(scope="session")
def staff(client):
    return login(client, "staff1", "staff123")
