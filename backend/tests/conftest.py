import pytest
from alembic.config import Config

from alembic import command
from app.database.database import create_database_engine
from app.models.profile import ProfileCreate
from app.services.profile_service import ProfileService


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("GRAVIA_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_database_engine(url)
    profile = ProfileService(engine).create_profile(ProfileCreate(name="Alfonso", height_cm=180))
    yield engine, profile, url
    engine.dispose()
