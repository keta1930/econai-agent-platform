"""Test infrastructure for the homework grading platform.

Uses an isolated test database (homework_test) with per-test table
creation/teardown. Provides fixtures for authenticated users at every
role level.
"""

import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from config import DB_HOST, DB_PORT, POSTGRES_USER, POSTGRES_PASSWORD

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

TEST_DB_NAME = "homework_test"
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"
)
# URL pointing at default 'postgres' db — used only to CREATE/DROP the test db
_ADMIN_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/postgres"
)


def pytest_configure(config: pytest.Config) -> None:
    """Ensure the test database exists before any test runs."""
    import asyncpg  # noqa: WPS433 — only needed here

    async def _ensure_db() -> None:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database="postgres",
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
        finally:
            await conn.close()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_ensure_db())


# Import Base *after* config is available so models register their tables
from database import Base  # noqa: E402
from models.user import User  # noqa: E402,F401 — ensure models loaded
from models.class_ import Class  # noqa: E402,F401
from models.roster import StudentRoster  # noqa: E402,F401
from models.task import Task  # noqa: E402,F401
from models.submission import Submission  # noqa: E402,F401
from models.sharing import SharingTopic, TopicVote  # noqa: E402,F401
from models.model_config import ModelConfig  # noqa: E402,F401
from models.backup import Backup  # noqa: E402,F401


@pytest_asyncio.fixture
async def db_engine() -> AsyncEngine:
    """Create a test engine (one per test)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncSession:
    """Per-test async session that rolls back nothing — tests own the schema lifecycle."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """httpx AsyncClient wired to the FastAPI app with the test DB session injected."""
    from main import app
    from database import get_db

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_user_in_db(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    role: str,
    class_id: uuid.UUID | None = None,
) -> User:
    """Insert a user directly via the ORM (bypasses API)."""
    from services.auth_service import hash_password

    pw_hash = hash_password(password)
    user = User(
        username=username,
        password_hash=pw_hash,
        role=role,
        class_id=class_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """Log in via the API and return the access_token."""
    resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Role-specific fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def super_admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    """Create a super_admin directly in DB and return its JWT token."""
    await _create_user_in_db(
        db_session,
        username="superadmin",
        password="superpass",
        role="super_admin",
    )
    return await _login(client, "superadmin", "superpass")


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, super_admin_token: str) -> str:
    """Create an admin via the super_admin API and return its JWT token."""
    resp = await client.post(
        "/api/super-admin/admins",
        json={"username": "testadmin", "password": "adminpass"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 201
    return await _login(client, "testadmin", "adminpass")


@pytest_asyncio.fixture
async def admin_with_class(
    client: AsyncClient, admin_token: str
) -> tuple[str, str]:
    """Create admin + one class. Returns (admin_token, class_id)."""
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "TestClass"},
        headers=auth_header(admin_token),
    )
    assert resp.status_code == 201
    class_id = resp.json()["id"]
    return admin_token, class_id


@pytest_asyncio.fixture
async def student_token(
    client: AsyncClient,
    admin_with_class: tuple[str, str],
    db_session: AsyncSession,
) -> str:
    """Register a student in the test class and return its JWT token."""
    token, class_id = admin_with_class

    # Add student to roster
    resp = await client.post(
        f"/api/admin/classes/{class_id}/roster",
        json={"student_id": "STU001"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201

    # Register student
    resp = await client.post(
        "/api/auth/register",
        json={
            "admin_name": "testadmin",
            "class_name": "TestClass",
            "student_id": "STU001",
            "password": "stupass",
        },
    )
    assert resp.status_code == 201

    return await _login(client, "STU001", "stupass")


@pytest_asyncio.fixture
async def another_admin_token(
    client: AsyncClient, super_admin_token: str
) -> str:
    """Create a second admin and return its JWT token."""
    resp = await client.post(
        "/api/super-admin/admins",
        json={"username": "otheradmin", "password": "otherpass"},
        headers=auth_header(super_admin_token),
    )
    assert resp.status_code == 201
    return await _login(client, "otheradmin", "otherpass")


@pytest_asyncio.fixture
async def another_admin_with_class(
    client: AsyncClient, another_admin_token: str
) -> tuple[str, str]:
    """Second admin with its own class. Returns (token, class_id)."""
    resp = await client.post(
        "/api/admin/classes",
        json={"name": "OtherClass"},
        headers=auth_header(another_admin_token),
    )
    assert resp.status_code == 201
    class_id = resp.json()["id"]
    return another_admin_token, class_id
