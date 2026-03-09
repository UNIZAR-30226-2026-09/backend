from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import select
from pydantic import BaseModel

from app.core.logica_juego.validaciones import validar_ataque_convencional
from app.core.logica_juego.combate import resolver_tirada
from app.api.v1.endpoints.usuarios import obtener_usuario_actual
from app.models.usuario import User
from app.models.partida import EstadoPartida
from app.db.session import get_db
from app.core.ws_manager import manager
from app.schemas.combate import AtaqueCreate 

router = APIRouter()


async def obtener_estado_partida(db: AsyncSession, partida_id: int):
    query = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
    resultado = await db.execute(query)
    estado = resultado.scalar_one_or_none()
    if not estado:
        raise HTTPException(404, "Estado de partida no encontrado")
    return estado


def obtener_datos_territorio(mapa: dict, territorio_id: str):
    territorios = mapa.get("territories", {})
    if territorio_id not in territorios:
        raise HTTPException(404, "Territorio no encontrado en el mapa")
    return territorios[territorio_id]


def aplicar_bajas(t_origen: dict, t_destino: dict, resultado):
    t_origen["units"] -= resultado.bajas_atacante
    t_destino["units"] -= resultado.bajas_defensor


def gestionar_victoria(t_destino: dict, resultado):
    if resultado.victoria_atacante:
        t_destino["status"] = "PENDING_OCCUPATION"


async def notificar_resultado(partida_id: int, origen_id: str, destino_id: str, resultado):
    evento_ws = {
        "tipo_evento": "ATAQUE_RESULTADO",
        "origen_id": origen_id,
        "destino_id": destino_id,
        "dados_atacante": resultado.dados_atacante,
        "dados_defensor": resultado.dados_defensor,
        "bajas_atacante": resultado.bajas_atacante,
        "bajas_defensor": resultado.bajas_defensor,
        "victoria": resultado.victoria_atacante
    }
    await manager.broadcast(evento_ws, partida_id)


@router.post("/partidas/{partida_id}/ataque", status_code=status.HTTP_200_OK)
async def ejecutar_ataque(
    partida_id: int,
    ataque_in: AtaqueCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado_partida = await obtener_estado_partida(db, partida_id)

    t_origen = obtener_datos_territorio(estado_partida.mapa, ataque_in.territorio_origen_id)
    t_destino = obtener_datos_territorio(estado_partida.mapa, ataque_in.territorio_destino_id)

    grafo_aragon = {}

    try:
        validar_ataque_convencional(
            estado_partida,
            ataque_in.territorio_origen_id,
            t_origen,
            ataque_in.territorio_destino_id,
            t_destino,
            ataque_in.tropas_a_mover,
            usuario_actual.username,
            grafo_aragon
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resultado = resolver_tirada(
        ataque_in.tropas_a_mover,
        t_destino["units"]
    )

    aplicar_bajas(t_origen, t_destino, resultado)
    gestionar_victoria(t_destino, resultado)

    flag_modified(estado_partida, "mapa")
    await db.commit()

    await notificar_resultado(
        partida_id, 
        ataque_in.territorio_origen_id, 
        ataque_in.territorio_destino_id, 
        resultado
    )

    return resultado