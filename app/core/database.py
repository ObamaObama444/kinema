from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    is_sqlite = url.startswith("sqlite")

    return create_engine(
        url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )


engine: Engine = get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
