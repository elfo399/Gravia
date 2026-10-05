from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

from alembic import context
from app.configuration import Settings
from app.models import (  # noqa: F401
    ActivitySession,
    BoardCalibration,
    Measurement,
    MeasurementSession,
    Profile,
)

target_metadata = SQLModel.metadata
url = Settings().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
