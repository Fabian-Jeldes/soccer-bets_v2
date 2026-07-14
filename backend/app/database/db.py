from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

# Configurar motor asíncrono
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Configurar creador de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        # Importar modelos aquí para registrarlos en la metadata
        from app.database.models import Match, SurebetOpportunity, Bet, PredictionMarketOpportunity, CrossMarketOpportunity
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
