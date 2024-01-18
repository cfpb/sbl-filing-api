from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from asyncio import current_task
from config import settings

engine = create_async_engine(settings.inst_conn.unicode_string(), echo=True).execution_options(
    schema_translate_map={None: settings.inst_db_schema}
)
SessionLocal = async_scoped_session(async_sessionmaker(engine, expire_on_commit=False), current_task)


async def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()
