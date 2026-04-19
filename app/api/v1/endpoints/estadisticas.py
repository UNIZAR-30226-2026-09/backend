from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.usuario import EstadisticaRead
from app.crud import crud_estadisticas
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User

router = APIRouter()

# ----------------------------------------------------------------------------
# 1. OBTENER RANKING GLOBAL
# ----------------------------------------------------------------------------
@router.get("/ranking", response_model=list[EstadisticaRead])
async def obtener_ranking(
    limite: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve el Top X de jugadores ordenados por victorias y soldados eliminados.
    """
    ranking = await crud_estadisticas.obtener_ranking_global(db, limite=limite)
    return ranking

# ----------------------------------------------------------------------------
# 2. OBTENER MIS ESTADÍSTICAS (Usuario Autenticado)
# ----------------------------------------------------------------------------
@router.get("/me", response_model=EstadisticaRead)
async def obtener_mis_estadisticas(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve las estadísticas detalladas del usuario que hace la petición.
    """
    stats = await crud_estadisticas.obtener_estadisticas(db, usuario_actual.username)
    if not stats:
        # Si por alguna razón no existen, las inicializamos al vuelo
        stats = await crud_estadisticas.inicializar_estadisticas(db, usuario_actual.username)
    return stats

# ----------------------------------------------------------------------------
# 3. OBTENER ESTADÍSTICAS DE OTRO USUARIO
# ----------------------------------------------------------------------------
@router.get("/{username}", response_model=EstadisticaRead)
async def obtener_estadisticas_usuario(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Permite consultar el perfil de estadísticas de cualquier jugador.
    """
    stats = await crud_estadisticas.obtener_estadisticas(db, username)
    if not stats:
        raise HTTPException(status_code=404, detail="Estadísticas no encontradas para este usuario")
    return stats