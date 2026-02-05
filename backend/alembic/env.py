from logging.config import fileConfig
import sys
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your models and Base
from app.core.database import Base
from app.models import (
    User,
    LLMConfig,
    Conversation,
    Message,
    Rule,
    ActionDefinition,
    GraphEntity,
    GraphRelationship,
    SchemaClass,
    SchemaRelationship,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 从环境变量读取 DATABASE_URL
from app.core.config import settings
database_url = settings.effective_database_url

# Alembic 需要使用同步驱动，将 asyncpg 替换为 psycopg2 或 postgresql+pg8000
# 为了迁移方便，直接替换 URL 前缀
if database_url.startswith("postgresql+asyncpg://"):
    sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
else:
    sync_database_url = database_url

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=sync_database_url,  # 使用同步 URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 使用同步 URL
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sync_database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
