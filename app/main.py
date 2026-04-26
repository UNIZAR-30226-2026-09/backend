from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from fastapi.staticfiles import StaticFiles
import os 

# =============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN (ENTRY POINT)
# =============================================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend oficial para el proyecto SOBERANÍA (Risk de Aragón).",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# ARCHIVOS ESTÁTICOS
# =============================================================================
os.makedirs("app/static/perfiles", exist_ok=True)
os.makedirs("app/static/reacciones", exist_ok=True) 
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# =============================================================================
# MIDDLEWARE: CORS (Seguridad de Navegador)
# =============================================================================
# Permite peticiones desde el Frontend (React) y el motor de juego (Flutter).
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# RUTAS
# =============================================================================
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "API Operativa", 
        "docs": "Ve a /docs para ver la documentación"
    }