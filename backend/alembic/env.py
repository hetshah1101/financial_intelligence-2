import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from alembic import context

# Make backend package importable from alembic's working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import engine, Base  # noqa: E402

# Import all models so their tables are registered on Base.metadata
import models  # noqa: F401, E402
import models_investment  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
