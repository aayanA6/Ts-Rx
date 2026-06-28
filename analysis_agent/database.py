from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from analysis_agent.config import get_settings

settings = get_settings()

_url = settings.database_url

# SQLite needs check_same_thread=False and doesn't support pool_pre_ping the same way
if _url.startswith("sqlite"):
    engine = create_async_engine(_url, connect_args={"check_same_thread": False})
else:
    engine = create_async_engine(_url, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
