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
from app.schemas.combate import AtaqueCreate, ResultadoCombate, MoverConquistaOut, PasarFaseOut, ColocarTropasOut
from app.schemas.estado_juego import TerritorioBase, JugadorBase
from app.crud import crud_combates
from app.core.logica_juego.validaciones import validar_colocacion_tropas
from app.core.logica_juego.combate import resolver_colocacion_tropas
from app.core.notifier import notifier


router = APIRouter()

#! Mover de aqui
# --- MODELOS DE DATOS ---
class MoverConquistaIn(BaseModel):
    tropas: int

class ColocarTropasIn(BaseModel):
    territorio_id: str
    tropas: int

#! Ayuda en api¿?
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

def verificar_movimiento_pendiente(jugadores: dict, jugador_id: str):
    datos_jugador_dict = jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)
    
    if jugador_estado.movimiento_conquista_pendiente:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST, 
             detail="Debes mover tropas al territorio conquistado antes de realizar otro ataque."
         )
    return jugador_estado


# --- MECÁNICAS DE JUEGO ---

@router.post("/partidas/{partida_id}/ataque", response_model=ResultadoCombate, status_code=status.HTTP_200_OK)
async def ejecutar_ataque(
    partida_id: int,
    ataque_in: AtaqueCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Evalúa y ejecuta un ataque entre territorios, calculando las tiradas de dados y las bajas.

    - **partida_id**: Identificador único de la partida.
    - **ataque_in**: Esquema con los datos del ataque (origen, destino, tropas).
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el resultado matemático y lógico del combate.
    """

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

    await notifier.enviar_resultado_ataque(
        partida_id, 
        ataque_in.territorio_origen_id, 
        ataque_in.territorio_destino_id, 
        resultado
    )
    return resultado


@router.post("/partidas/{partida_id}/mover_conquista", response_model=MoverConquistaOut, status_code=status.HTTP_200_OK)
async def mover_tropas_conquista(
    partida_id: int,
    datos: MoverConquistaIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    
    """
    Ejecuta el movimiento obligatorio de tropas hacia un territorio recientemente conquistado.

    - **partida_id**: Identificador único de la partida.
    - **datos**: Esquema con el número de tropas a movilizar.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un mensaje de confirmación de la operación.
    """
    
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
    await notifier.enviar_movimiento_conquista(
        partida_id, origen_id, destino_id, datos.tropas, jugador_id
    )

    return {"mensaje": f"Has movilizado {datos.tropas} tropas a tu nuevo territorio"}


@router.post("/partidas/{partida_id}/pasar_fase", response_model=PasarFaseOut, status_code=status.HTTP_200_OK)
async def pasar_fase_manual(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    
    """
    Avanza manualmente la fase actual del turno del jugador (ej. de Refuerzo a Combate).

    - **partida_id**: Identificador único de la partida.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna la información actualizada de la nueva fase y a quién corresponde el turno.
    """

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


@router.post("/partidas/{partida_id}/colocar_tropas", response_model=ColocarTropasOut, status_code=status.HTTP_200_OK)
async def colocar_tropas_reserva(
    partida_id: int,
    datos: ColocarTropasIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Permite al jugador en turno desplegar tropas de su reserva en un territorio controlado.

    - **partida_id**: Identificador único de la partida.
    - **datos**: Esquema con el territorio de destino y la cantidad de tropas.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un estado indicando el éxito del despliegue y la reserva restante.
    """

    estado_partida = await obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    
    t_destino = obtener_datos_territorio(estado_partida.mapa, datos.territorio_id)
    datos_jugador_dict = estado_partida.jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)

    try:
        validar_colocacion_tropas(
            estado_partida, jugador_id, datos.territorio_id, 
            t_destino, datos.tropas, jugador_estado.tropas_reserva
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resolver_colocacion_tropas(jugador_estado, t_destino, datos.tropas)

    estado_partida.mapa[datos.territorio_id] = t_destino.model_dump()
    estado_partida.jugadores[jugador_id] = jugador_estado.model_dump()
    await crud_combates.guardar_estado_partida(db, estado_partida)

    await notifier.enviar_tropas_colocadas(
        partida_id, jugador_id, datos.territorio_id, datos.tropas, t_destino.units
    )

    return {
        "mensaje": f"Has metido {datos.tropas} soldados en {datos.territorio_id}",
        "reserva_restante": jugador_estado.tropas_reserva
    }


# # ----------------------------------------------------------------------------
# # RUTA DE TEST PARA COMPROBAR LOS DADOS (T9)
# # ----------------------------------------------------------------------------
# @router.get("/test-dados", response_model=ResultadoCombate)
# async def probar_dados_de_guerra(tropas_atacantes: int = 3, tropas_defensoras: int = 2):
#     resultado = resolver_tirada(tropas_atacantes, tropas_defensoras)
#     return resultado