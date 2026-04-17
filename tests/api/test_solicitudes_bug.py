import os
import pytest
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "clave-secreta-de-mentira-para-tests"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def _reg_login(client, username):
    client.post("/api/v1/usuarios/registro", json={"username": username, "email": f"{username}@test.com", "password": "password123"})
    res = client.post("/api/v1/usuarios/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_listar_solicitudes_pendientes(client):
    h1 = _reg_login(client, "alice")
    h2 = _reg_login(client, "bob")
    
    # Alice sends friend request to Bob
    res = client.post("/api/v1/amigos/solicitar", json={"user_2": "bob"}, headers=h1)
    print(f"Solicitar response: {res.status_code} {res.json()}")
    assert res.status_code == 200
    
    # Bob lists pending requests
    res = client.get("/api/v1/amigos/solicitudes", headers=h2)
    print(f"Solicitudes response: {res.status_code} {res.json()}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.json()}"
    data = res.json()
    assert len(data) == 1
    print(f"Request data: {data[0]}")
