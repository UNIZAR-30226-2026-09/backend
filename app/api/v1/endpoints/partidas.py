from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import random
import string
import asyncio
from datetime import datetime, timedelta, timezone

from app.schemas.partida import PartidaCreate, PartidaRead, JugadorPartidaRead, VotoPausa
from app.schemas.partida import AccionPausaOut, EmpezarPartidaOut, VerEstadoPartidaOut
from app.models.partida import EstadosPartida, ColorJugador, EstadoPartida, FasePartida
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User
from app.db.session import get_db
from app.crud import crud_partidas

# Cosas nuevas para empezar la partida
from app.core.map_state import game_map_state
from app.core.logica_juego.inicializacion import generar_reparto_inicial
from app.core.logica_juego.maquina_estados import iniciar_temporizador, tareas_en_segundo_plano

from app.core.ws_manager import manager
from app.core.notifier import notifier


router = APIRouter()

#! Mover de aqui
# Fabrica codigos de 6 letras/numeros al azar
def generar_codigo_invitacion():
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=6))

# --- PARTIDAS ---

@router.post("", response_model=PartidaRead)
async def crear_partida(
    partida_in: PartidaCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nueva partida, genera un código único de invitación y añade al anfitrión como primer jugador.

    - **partida_in**: Esquema de configuración de la partida (máximo de jugadores, visibilidad, temporizador).
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado (creador).
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna los datos de la partida creada.
    """

    nuevo_codigo = generar_codigo_invitacion()
    
    nueva_partida = await crud_partidas.crear_partida_y_creador(
        db,
        partida_in,
        nuevo_codigo,
        usuario_actual.username
    )
    
    return nueva_partida

@router.get("", response_model=list[PartidaRead])
async def listar_partidas_publicas(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el listado de partidas públicas disponibles en el sistema.

    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna una lista de partidas configuradas como públicas.
    """
    #! Validad usuario actual ¿?
    return await crud_partidas.obtener_partidas_publicas(db)

@router.post("/{codigo}/unirse", response_model=JugadorPartidaRead)
async def unirse_partida(
    codigo: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Permite a un usuario unirse a una partida existente utilizando su código de invitación.

    - **codigo**: Cadena alfanumérica única que identifica la sala.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna la información del jugador tras unirse a la sala.
    """

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

    await notifier.notificar_nuevo_jugador(
        partida_id=partida.id,
        username=usuario_actual.username,
        color=nuevo_jugador.color.value
    )

    return nuevo_jugador

@router.post("/{partida_id}/empezar", response_model=EmpezarPartidaOut, status_code=status.HTTP_200_OK)
async def empezar_partida(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Inicia una partida en fase de creación. Genera el reparto inicial del mapa e inicia los temporizadores.
    Solo puede ser ejecutado por el creador de la partida.

    - **partida_id**: Identificador único de la partida.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un diccionario con el estado inicial de la partida (mensaje, id, turno inicial y fase).
    """

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
    estado_jugadores = {
        j.usuario_id: {
            "tropas_reserva": 10,
            "color": j.color.value
        } for j in jugadores 
    }

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

    await notifier.enviar_inicio_partida(
        partida_id=partida.id,
        mapa=mapa_repartido,
        jugadores=estado_jugadores,
        turno_de=jugador_creador.usuario_id,
        fin_fase=fin_fase
    )

    return {
        "mensaje": "¡Aragón está en guerra!", 
        "partida_id": partida.id, 
        "turno_de": jugador_creador.usuario_id,
        "fase": "refuerzo"
    }

@router.get("/{partida_id}/estado", response_model=VerEstadoPartidaOut, status_code=status.HTTP_200_OK)
async def ver_estado_partida(
    partida_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el estado actual del tablero, los jugadores y las fases de una partida activa.

    - **partida_id**: Identificador único de la partida.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un objeto estructurado con el estado completo de la partida.
    """
    
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

@router.post("/{code}/reanudar", response_model=AccionPausaOut, status_code=status.HTTP_200_OK)
async def reanudar_partida(
    code: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Inicia la recuperación de una partida pausada.

    - **code**: Código único de 6 caracteres de la partida.
    - **usuario_actual**: El usuario que reanuda la partida (host)
    - **db**: Sesión de base de datos asíncrona.
    """
    raise HTTPException(status_code=501, detail="No implementado")

@router.post("/{code}/pausa/solicitar", response_model=AccionPausaOut, status_code=status.HTTP_200_OK)
async def solicitar_pausa(
    code: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Cualquier jugador puede llamar a esto para abrir una votación de pausa.
    
    - **code**: Código único de 6 caracteres de la partida.
    - **usuario_actual**: El jugador que propone pausar el juego.
    - **db**: Sesión de base de datos asíncrona.
    """
    raise HTTPException(status_code=501, detail="No implementado")


@router.post("/{code}/pausa/votar", response_model=AccionPausaOut, status_code=status.HTTP_200_OK)
async def votar_pausa(
    code: str,
    voto_in: VotoPausa,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Los jugadores usan este endpoint para votar si quieren pausar o no.
    Si los votos a favor alcanzan la mayoría, el estado pasará a PAUSED.

    - **code**: Código único de 6 caracteres de la partida.
    - **voto_in**: Booleano indicando si vota que SÍ (true) o que NO (false).
    - **usuario_actual**: El jugador que emite el voto.
    - **db**: Sesión de base de datos asíncrona.
    """
    raise HTTPException(status_code=501, detail="No implementado")