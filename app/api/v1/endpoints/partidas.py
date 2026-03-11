from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import random
import string
import asyncio
from datetime import datetime, timedelta, timezone

from app.schemas.partida import PartidaCreate, PartidaRead, JugadorPartidaRead
from app.models.partida import EstadosPartida, ColorJugador, EstadoPartida, FasePartida
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User
from app.db.session import get_db
from app.crud import crud_partidas

# Cosas nuevas para empezar la partida
from app.core.map_state import game_map_state
from app.core.logica_juego.inicializacion import generar_reparto_inicial
from app.core.logica_juego.maquina_estados import iniciar_temporizador, tareas_en_segundo_plano

router = APIRouter()

# Fabrica codigos de 6 letras/numeros al azar
def generar_codigo_invitacion():
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=6))

# ----------------------------------------------------------------------------
# 1. CREAR PARTIDA
# ----------------------------------------------------------------------------
@router.post("", response_model=PartidaRead)
async def crear_partida(
    partida_in: PartidaCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    nuevo_codigo = generar_codigo_invitacion()
    
    nueva_partida = await crud_partidas.crear_partida_y_creador(
        db,
        partida_in,
        nuevo_codigo,
        usuario_actual.username
    )
    
    return nueva_partida

# ----------------------------------------------------------------------------
# 2. LISTAR PARTIDAS PÚBLICAS
# ----------------------------------------------------------------------------
@router.get("", response_model=list[PartidaRead])
async def listar_partidas_publicas(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    return await crud_partidas.obtener_partidas_publicas(db)

# ----------------------------------------------------------------------------
# 3. UNIRSE A UNA PARTIDA
# ----------------------------------------------------------------------------
@router.post("/{codigo}/unirse", response_model=JugadorPartidaRead)
async def unirse_partida(
    codigo: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    partida = await crud_partidas.obtener_partida_por_codigo(db, codigo)

    if not partida:
        raise HTTPException(status_code=404, detail="Ese código no existe, revisa bien")
    
    if partida.estado != EstadosPartida.CREANDO:
        raise HTTPException(status_code=400, detail="La partida ya ha empezado o está cerrada")

    jugadores_actuales = await crud_partidas.obtener_jugadores_partida(db, partida.id)

    if len(jugadores_actuales) >= partida.config_max_players:
        raise HTTPException(status_code=400, detail="La sala está llena")

    for j in jugadores_actuales:
        if j.usuario_id == usuario_actual.username:
            raise HTTPException(status_code=400, detail="Ya estás dentro de esta partida")

    colores_usados = {j.color for j in jugadores_actuales}
    todos_colores = set(ColorJugador)
    colores_libres = list(todos_colores - colores_usados)
    
    nuevo_jugador = await crud_partidas.unir_jugador(
        db,
        usuario_actual.username,
        partida.id,
        len(jugadores_actuales) + 1,
        colores_libres[0]
    )

    return nuevo_jugador

# ----------------------------------------------------------------------------
# 4. EMPEZAR LA PARTIDA (El pistoletazo de salida)
# ----------------------------------------------------------------------------
@router.post("/{partida_id}/empezar")
async def empezar_partida(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos la partida
    partida = await crud_partidas.obtener_partida_por_id(db, partida_id)

    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
        
    if partida.estado != EstadosPartida.CREANDO:
        raise HTTPException(status_code=400, detail="La partida ya ha empezado o está finalizada")

    # Sacamos a los que están sentados en la mesa
    jugadores = await crud_partidas.obtener_jugadores_partida(db, partida_id)

    if len(jugadores) < 2:
        raise HTTPException(status_code=400, detail="Mínimo 2 jugadores para darse de tortas")

    # Controlamos que no le dé al botón cualquiera, solo el admin de la sala (turno 1)
    jugador_creador = next((j for j in jugadores if j.turno == 1), None)
    if not jugador_creador or jugador_creador.usuario_id != usuario_actual.username:
        raise HTTPException(status_code=403, detail="Tú no mandas aquí, solo el creador puede empezar")

    # Preparamos los datos para tu colega
    jugadores_ids = [j.usuario_id for j in jugadores]
    comarcas_ids = list(game_map_state.comarcas.keys())
    
    # Repartimos Aragón
    mapa_repartido = generar_reparto_inicial(jugadores_ids, comarcas_ids)
    
    # Les damos 10 tropas a cada uno de regalo para colocar en el primer turno
    estado_jugadores = {j_id: {"tropas_reserva": 10} for j_id in jugadores_ids}

    # Creamos el tablero real (T8)
    fin_fase = datetime.now(timezone.utc) + timedelta(seconds=partida.config_timer_seconds)
    
    nuevo_estado = EstadoPartida(
        partida_id=partida.id,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=fin_fase,
        user_turno_actual=jugador_creador.usuario_id,
        mapa=mapa_repartido,
        jugadores=estado_jugadores
    )

    # Guardamos el inicio de la partida (estado ACTIVA + EstadoPartida)
    await crud_partidas.guardar_inicio_partida(db, partida, nuevo_estado)

    # Le damos al cronómetro invisible y lo metemos en la lista fuerte
    tarea_inicio = asyncio.create_task(iniciar_temporizador(partida.id, FasePartida.REFUERZO, fin_fase))
    tareas_en_segundo_plano.add(tarea_inicio)
    tarea_inicio.add_done_callback(tareas_en_segundo_plano.discard)

    return {
        "mensaje": "¡Aragón está en guerra!", 
        "partida_id": partida.id, 
        "turno_de": jugador_creador.usuario_id,
        "fase": "refuerzo"
    }

# ----------------------------------------------------------------------------
# 5. VER ESTADO DE LA PARTIDA (La mirilla)
# ----------------------------------------------------------------------------
@router.get("/{partida_id}/estado")
async def ver_estado_partida(
    partida_id: int,
    db: AsyncSession = Depends(get_db)
):
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)

    if not estado:
        raise HTTPException(status_code=404, detail="No hay estado para esta partida")

    return {
        "turno_de": estado.user_turno_actual,
        "fase_actual": estado.fase_actual.value,
        "fin_fase_utc": estado.fin_fase_actual,
        "mapa": estado.mapa,
        "jugadores": estado.jugadores
    }