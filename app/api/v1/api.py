from fastapi import APIRouter
from app.api.v1.endpoints import usuarios, websockets, mapa, partidas, amigos

# =============================================================================
# ROUTER PRINCIPAL (V1)
# =============================================================================
api_router = APIRouter()

# Aquí enganchamos todas las rutas que hemos ido creando
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["Usuarios"])
api_router.include_router(mapa.router, prefix="/mapa", tags=["Mapa"])
api_router.include_router(partidas.router, prefix="/partidas", tags=["Partidas"])
api_router.include_router(amigos.router, prefix="/amigos", tags=["Amigos"])

api_router.include_router(websockets.router, tags=["WebSockets"])

@api_router.get("/status", tags=["Sistema"])
async def check_api_status():
    """Health Check para Docker"""
    return {"status": "ok", "version": "v1", "project": "SOBERANIA"}