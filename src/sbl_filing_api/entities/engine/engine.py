from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from sbl_filing_api.config import settings

engine = create_engine(settings.conn.unicode_string(), echo=settings.db_logging, poolclass=NullPool).execution_options(
    schema_translate_map={None: settings.db_schema}
)
SessionLocal = scoped_session(sessionmaker(engine, expire_on_commit=False))


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
