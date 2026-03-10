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
from app.schemas.estado_juego import TerritorioBase, JugadorBase

router = APIRouter()


async def obtener_estado_partida(db: AsyncSession, partida_id: int):
    query = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
    resultado = await db.execute(query)
    estado = resultado.scalar_one_or_none()
    if not estado:
        raise HTTPException(404, "Estado de partida no encontrado")
    return estado


def obtener_datos_territorio(mapa: dict, territorio_id: str) -> TerritorioBase:
    if territorio_id not in mapa:
        raise HTTPException(status_code=404, detail="Territorio no encontrado en el mapa")
    return TerritorioBase(**mapa[territorio_id])


def aplicar_bajas(t_origen: dict, t_destino: dict, resultado):
    t_origen.units -= resultado.bajas_atacante
    t_destino.units -= resultado.bajas_defensor


def gestionar_victoria(
        t_destino: TerritorioBase, jugador_estado: JugadorBase, 
        atacante_id: str, origen_id: str, destino_id: str, resultado):
    
    if resultado.victoria_atacante:
        t_destino.owner_id = atacante_id

        # Mover tropas
        jugador_estado.movimiento_conquista_pendiente = True
        
        jugador_estado.origen_conquista = origen_id
        jugador_estado.destino_conquista = destino_id


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


def verificar_movimiento_pendiente(jugadores: dict, jugador_id: str):
    datos_jugador_dict = jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)
    
    if jugador_estado.movimiento_conquista_pendiente:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST, 
             detail="Debes mover tropas al territorio conquistado antes de realizar otro ataque."
         )
    
    return jugador_estado

@router.post("/partidas/{partida_id}/ataque", status_code=status.HTTP_200_OK)
async def ejecutar_ataque(
    partida_id: int,
    ataque_in: AtaqueCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado_partida = await obtener_estado_partida(db, partida_id)
    atacante_id = usuario_actual.username

    jugador_estado = verificar_movimiento_pendiente(estado_partida.jugadores, atacante_id)

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
            atacante_id,
            grafo_aragon
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resultado = resolver_tirada(
        ataque_in.tropas_a_mover,
        t_destino.units
    )

    aplicar_bajas(t_origen, t_destino, resultado)

    gestionar_victoria(
        t_destino, 
        jugador_estado, 
        atacante_id, 
        ataque_in.territorio_origen_id, 
        ataque_in.territorio_destino_id, 
        resultado
    )

    estado_partida.mapa[ataque_in.territorio_origen_id] = t_origen.model_dump()
    estado_partida.mapa[ataque_in.territorio_destino_id] = t_destino.model_dump()
    estado_partida.jugadores[atacante_id] = jugador_estado.model_dump()

    flag_modified(estado_partida, "mapa")
    flag_modified(estado_partida, "jugadores")
    await db.commit()

    await notificar_resultado(
        partida_id, 
        ataque_in.territorio_origen_id, 
        ataque_in.territorio_destino_id, 
        resultado
    )

    return resultado