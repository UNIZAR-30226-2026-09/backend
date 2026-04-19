from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine_args = {
    "echo": False
}

if "sqlite" not in settings.DATABASE_URL:
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 0
    engine_args["pool_pre_ping"] = True
    engine_args["connect_args"] = {
        "ssl": True,
        "statement_cache_size": 0,  # evita el error "cache lookup failed for type OID" en asyncpg
    }

# Motor de conexión asíncrono dinámico
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_args
)

# Fábrica de sesiones
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependencia para inyectar la sesión en los endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()