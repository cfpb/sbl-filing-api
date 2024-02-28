import os
from urllib import parse
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from dotenv import load_dotenv

from entities.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# this specific to SBL configuration

ENV = os.getenv("ENV", "LOCAL")

if ENV == "LOCAL":
    file_dir = os.path.dirname(os.path.realpath(__file__))
    load_dotenv(f"{file_dir}/../src/.env.local")
else:
    load_dotenv()

DB_USER = os.environ.get("DB_USER")
DB_PWD = os.environ.get("DB_PWD")
DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_SCHEMA = os.environ.get("DB_SCHEMA")
CONN = f"postgresql://{DB_USER}:{(parse.quote(DB_PWD, safe='')).replace('%', '%%')}@{DB_HOST}/{DB_NAME}"
config.set_main_option("sqlalchemy.url", CONN)

# end specific SBL configuration

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel

target_metadata = Base.metadata
target_metadata.schema = DB_SCHEMA

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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=target_metadata.schema,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()