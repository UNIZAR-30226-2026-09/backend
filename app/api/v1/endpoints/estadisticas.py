from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.usuario import EstadisticaRead, RankingItemOut
from app.crud import crud_estadisticas
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User

router = APIRouter()

# ----------------------------------------------------------------------------
# 1. OBTENER RANKING GLOBAL
# ----------------------------------------------------------------------------
@router.get("/ranking", response_model=list[RankingItemOut])
async def obtener_ranking(
    limite: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve el Top X de jugadores ordenados por victorias y soldados eliminados.
    
    El desempate se realiza por el número de soldados matados (el más letal gana).
    Pydantic calculará automáticamente el 'winrate' de cada jugador.
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
    Incluye campos calculados como la región más conquistada y el winrate.
    """
    stats = await crud_estadisticas.obtener_estadisticas(db, usuario_actual.username)
    if not stats:
        # Inicialización automática si es la primera vez que consulta
        stats = await crud_estadisticas.inicializar_estadisticas(db, usuario_actual.username)

    posicion = await crud_estadisticas.obtener_posicion_ranking(db, usuario_actual.username)
    return EstadisticaRead.model_validate(stats).model_copy(update={"posicion_ranking": posicion})

# ----------------------------------------------------------------------------
# 3. OBTENER ESTADÍSTICAS DE OTRO USUARIO
# ----------------------------------------------------------------------------
@router.get("/{username}", response_model=EstadisticaRead)
async def obtener_estadisticas_usuario(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Permite consultar el perfil de estadísticas de cualquier jugador por su nombre.
    """
    stats = await crud_estadisticas.obtener_estadisticas(db, username)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Estadísticas no encontradas para el usuario '{username}'"
        )
    return stats