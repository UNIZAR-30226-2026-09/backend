from fastapi import APIRouter, Depends
from app.schemas.partida import PartidaCreate, PartidaRead
from app.models.partida import EstadosPartida
from app.api.v1.endpoints.usuarios import obtener_usuario_actual
from app.models.usuario import User

router = APIRouter()

@router.post("", response_model=PartidaRead)
async def crear_partida(
    partida_in: PartidaCreate,
    usuario_actual: User = Depends(obtener_usuario_actual)
):
    # TODO: Más adelante lo guardaremos en Neon. 
    # Por ahora devolvemos un JSON perfecto para que Frontend vaya probando.
    return PartidaRead(
        id=105,
        config_max_players=partida_in.config_max_players,
        config_visibility=partida_in.config_visibility,
        codigo_invitacion="A8F9B2",
        config_timer_seconds=partida_in.config_timer_seconds,
        estado=EstadosPartida.CREANDO,
        ganador=None
    )