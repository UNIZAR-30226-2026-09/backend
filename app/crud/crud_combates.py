from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.partida import EstadoPartida

# ----------------------------------------------------------------------------
# 1. GUARDAR ESTADO DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def guardar_estado_partida(db: AsyncSession, estado_partida: EstadoPartida) -> None:
    """
    Marca los campos JSONB (mapa y jugadores) como modificados y hace commit.
    Esta función es necesaria porque SQLAlchemy no detecta automáticamente 
    cambios dentro de campos JSON.
    
    Args:
        db: Sesión de base de datos
        estado_partida: Objeto EstadoPartida a guardar
        
    Returns:
        None
    """
    flag_modified(estado_partida, "mapa")
    flag_modified(estado_partida, "jugadores")
    await db.commit()
