from fastapi import APIRouter
from app.api.v1.endpoints import usuarios, websockets

# =============================================================================
# ROUTER PRINCIPAL (V1)
# =============================================================================
api_router = APIRouter()

# Aquí es donde enganchamos las rutas de usuarios que acabas de crear
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])

api_router.include_router(websockets.router, tags=["WebSockets"])

@api_router.get("/status", tags=["Sistema"])
async def check_api_status():
    """Health Check para Docker"""
    return {"status": "ok", "version": "v1", "project": "SOBERANIA"}