from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.map_state import map_calculator
from app.core.logica_juego.validaciones import validar_ataque_convencional
from app.core.logica_juego.combate import resolver_tirada
from app.core.logica_juego.maquina_estados import avanzar_fase
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User
from app.db.session import get_db
from app.core.ws_manager import manager
from app.schemas.combate import AtaqueCreate, ResultadoCombate
from app.schemas.estado_juego import TerritorioBase, JugadorBase
from app.crud import crud_combates
from app.core.logica_juego.validaciones import validar_colocacion_tropas
from app.core.logica_juego.combate import resolver_colocacion_tropas

router = APIRouter()

# --- MODELOS DE DATOS ---
class MoverConquistaIn(BaseModel):
    tropas: int

class ColocarTropasIn(BaseModel):
    territorio_id: str
    tropas: int

# --- FUNCIONES DE AYUDA ---
async def obtener_estado_partida(db: AsyncSession, partida_id: int):
    """Función adaptadora que llama al CRUD y lanza HTTPException si no existe."""
    estado = await crud_combates.obtener_estado_partida(db, partida_id)
    if not estado:
        raise HTTPException(404, "Estado de partida no encontrado")
    return estado

def obtener_datos_territorio(mapa: dict, territorio_id: str) -> TerritorioBase:
    if territorio_id not in mapa:
        raise HTTPException(status_code=404, detail="Territorio no encontrado en el mapa")
    return TerritorioBase(**mapa[territorio_id])

def aplicar_bajas(t_origen: TerritorioBase, t_destino: TerritorioBase, resultado):
    t_origen.units -= resultado.bajas_atacante
    t_destino.units -= resultado.bajas_defensor

def gestionar_victoria(
        t_destino: TerritorioBase, jugador_estado: JugadorBase, 
        atacante_id: str, origen_id: str, destino_id: str, resultado):
    
    if resultado.victoria_atacante:
        t_destino.owner_id = atacante_id
        # Activamos el flag para que el jugador esté obligado a mover tropas
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


# ----------------------------------------------------------------------------
# RUTA 1: ATACAR
# ----------------------------------------------------------------------------
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

    try:
        validar_ataque_convencional(
            estado_partida, ataque_in.territorio_origen_id, t_origen,
            ataque_in.territorio_destino_id, t_destino,
            ataque_in.tropas_a_mover, atacante_id, map_calculator
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resultado = resolver_tirada(ataque_in.tropas_a_mover, t_destino.units)
    aplicar_bajas(t_origen, t_destino, resultado)

    gestionar_victoria(
        t_destino, jugador_estado, atacante_id, 
        ataque_in.territorio_origen_id, ataque_in.territorio_destino_id, resultado
    )

    estado_partida.mapa[ataque_in.territorio_origen_id] = t_origen.model_dump()
    estado_partida.mapa[ataque_in.territorio_destino_id] = t_destino.model_dump()
    estado_partida.jugadores[atacante_id] = jugador_estado.model_dump()

    await crud_combates.guardar_estado_partida(db, estado_partida)

    await notificar_resultado(partida_id, ataque_in.territorio_origen_id, ataque_in.territorio_destino_id, resultado)

    return resultado


# ----------------------------------------------------------------------------
# RUTA 2: MOVER TROPAS TRAS CONQUISTAR
# ----------------------------------------------------------------------------
@router.post("/partidas/{partida_id}/mover_conquista", status_code=status.HTTP_200_OK)
async def mover_tropas_conquista(
    partida_id: int,
    datos: MoverConquistaIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    
    datos_jugador_dict = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)

    if not jugador_estado.movimiento_conquista_pendiente:
        raise HTTPException(400, "No has conquistado nada recientemente")

    origen_id = jugador_estado.origen_conquista
    destino_id = jugador_estado.destino_conquista

    t_origen = obtener_datos_territorio(estado_partida.mapa, origen_id)
    t_destino = obtener_datos_territorio(estado_partida.mapa, destino_id)

    if t_origen.units <= datos.tropas:
        raise HTTPException(400, "Tienes que dejar al menos 1 guarnición en el territorio de origen")

    # Movemos los monigotes
    t_origen.units -= datos.tropas
    t_destino.units += datos.tropas

    # Limpiamos el chivato de conquista
    jugador_estado.movimiento_conquista_pendiente = False
    jugador_estado.origen_conquista = None
    jugador_estado.destino_conquista = None

    estado_partida.mapa[origen_id] = t_origen.model_dump()
    estado_partida.mapa[destino_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()

    await crud_combates.guardar_estado_partida(db, estado_partida)

    # Avisamos al front
    await manager.broadcast({
        "tipo_evento": "MOVIMIENTO_CONQUISTA",
        "origen": origen_id,
        "destino": destino_id,
        "tropas": datos.tropas,
        "jugador": jugador_id
    }, partida_id)

    return {"mensaje": f"Has movilizado {datos.tropas} tropas a tu nuevo territorio"}


# ----------------------------------------------------------------------------
# RUTA 3: PASAR DE FASE A MANO
# ----------------------------------------------------------------------------
@router.post("/partidas/{partida_id}/pasar_fase", status_code=status.HTTP_200_OK)
async def pasar_fase_manual(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado_partida = await obtener_estado_partida(db, partida_id)
    
    if estado_partida.user_turno_actual != usuario_actual.username:
        raise HTTPException(403, "Quieto ahí, no es tu turno")

    nuevo_estado = await avanzar_fase(partida_id, db, estado_partida.fase_actual)
    if not nuevo_estado:
        raise HTTPException(400, "Error al avanzar la fase")

    return {
        "mensaje": "Fase completada", 
        "nueva_fase": nuevo_estado.fase_actual.value,
        "turno_de": nuevo_estado.user_turno_actual
    }


@router.post("/partidas/{partida_id}/colocar_tropas", status_code=status.HTTP_200_OK)
async def colocar_tropas_reserva(
    partida_id: int,
    datos: ColocarTropasIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # 1. EL MOZO DE ALMACÉN SACA LOS INGREDIENTES
    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    
    t_destino = obtener_datos_territorio(estado_partida.mapa, datos.territorio_id)
    datos_jugador_dict = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)

    # 2. EL CHEF REVISA Y COCINA
    try:
        validar_colocacion_tropas(
            estado_partida, jugador_id, datos.territorio_id, 
            t_destino, datos.tropas, jugador_estado.tropas_reserva
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resolver_colocacion_tropas(jugador_estado, t_destino, datos.tropas)

    # 3. EL MOZO DE ALMACÉN GUARDA EL PLATO
    estado_partida.mapa[datos.territorio_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()
    await crud_combates.guardar_estado_partida(db, estado_partida)

    # 4. EL JEFE DE SALA AVISA A TODOS
    await manager.broadcast({
        "tipo_evento": "TROPAS_COLOCADAS",
        "jugador": jugador_id,
        "territorio": datos.territorio_id,
        "tropas_añadidas": datos.tropas,
        "tropas_totales_ahora": t_destino.units
    }, partida_id)

    return {
        "mensaje": f"Has metido {datos.tropas} soldados en {datos.territorio_id}",
        "reserva_restante": jugador_estado.tropas_reserva
    }


# ----------------------------------------------------------------------------
# RUTA DE TEST PARA COMPROBAR LOS DADOS (T9)
# ----------------------------------------------------------------------------
@router.get("/test-dados", response_model=ResultadoCombate)
async def probar_dados_de_guerra(tropas_atacantes: int = 3, tropas_defensoras: int = 2):
    resultado = resolver_tirada(tropas_atacantes, tropas_defensoras)
    return resultado