from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 1. Preparamos los argumentos base compartidos
engine_args = {
    "echo": False
}

# 2. Si la base de datos NO es SQLite (es decir, es PostgreSQL), añadimos el pooling
if "sqlite" not in settings.DATABASE_URL:
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 0
    engine_args["pool_pre_ping"] = True

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