import os
import pytest
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# Truco Jedi para que SQLite entienda el JSONB de PostgreSQL en los tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# 0. EL ENGAÑO A PYDANTIC: Seteamos las variables obligatorias ANTES de importar la app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "clave-secreta-de-mentira-para-tests"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Importamos cosas de nuestra app
from app.main import app
from app.db.session import get_db
from app.db.base import Base

# 1. Creamos un motor de base de datos "de usar y tirar" en la memoria RAM
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

# 2. Reemplazamos el "mozo de almacén" real por el de pruebas
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

# Le decimos a FastAPI que cuando alguien pida `get_db`, use nuestro `override_get_db`
app.dependency_overrides[get_db] = override_get_db

# 3. Preparamos las tablas antes de cada test y las borramos al terminar
@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # Aquí se ejecuta el test
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# 4. Creamos el "Cliente Falso" que simulará ser Postman/Frontend
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 5. Proveedor de la sesión de BD
@pytest.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session