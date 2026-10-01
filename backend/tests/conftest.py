import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "pytest-secret-key-with-at-least-32-bytes"
os.environ["ALGORITHM"] = "HS256"

from app.main import app, create_token, get_db
from app.models.orm_models import Base, LifecycleStage, Model, Version


@dataclass
class ApiHarness:
    client: TestClient
    sessions: async_sessionmaker[AsyncSession]

    def auth(self, role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_token(role)}"}


@pytest.fixture
def api(tmp_path: Path):
    database_path = tmp_path / "api-tests.sqlite"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
        poolclass=NullPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    async def override_get_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    harness = ApiHarness(TestClient(app), sessions)
    yield harness
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


async def seed_model_and_versions(
    sessions: async_sessionmaker[AsyncSession],
    approval_status: str = "PENDING",
) -> tuple[int, int, int]:
    async with sessions() as session:
        model = Model(
            name="Test Model",
            framework="scikit-learn",
            algorithm="random-forest",
            tags="test",
        )
        session.add(model)
        await session.flush()
        first = Version(
            model_id=model.id,
            version_number=1,
            artifact_uri="/tmp/model-v1.bin",
            training_data_ref="train-v1",
            approval_status=approval_status,
            lifecycle_stage=LifecycleStage.VALIDATED,
        )
        second = Version(
            model_id=model.id,
            version_number=2,
            artifact_uri="/tmp/model-v2.bin",
            training_data_ref="train-v2",
            approval_status="APPROVED",
            lifecycle_stage=LifecycleStage.APPROVED,
        )
        session.add_all([first, second])
        await session.commit()
        return model.id, first.id, second.id