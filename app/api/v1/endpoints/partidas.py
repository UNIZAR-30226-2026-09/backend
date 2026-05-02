from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
import random
import string
import asyncio
from datetime import datetime, timedelta, timezone


from app.core.map_state import map_calculator
from app.core.logica_juego.validaciones import validar_fortificacion, validar_asignar_trabajo, validar_asignar_investigacion
from app.core.logica_juego.constantes import HABILIDADES, ARBOL_TECNOLOGICO
from app.core.logica_juego.config_ataques_especiales import CONFIG_ATAQUES
from app.core.logica_juego.combate import resolver_fortificacion
from app.core.logica_juego.utils import obtener_datos_territorio
from app.schemas.estado_juego import TerritorioBase

from app.schemas.partida import PartidaCreate, PartidaRead, VotoPausa
from app.schemas.partida import AccionPausaOut, EmpezarPartidaOut, VerEstadoPartidaOut, PartidaActivaOut, UnirseOut, AbandonarOut
from app.schemas.partida import FortificarIn, TecnologiasPartidaOut, HabilidadOut
from app.schemas.partida import AsignarTrabajoIn, AsignarInvestigacionIn, ComprarTecnologiaIn, LogPartidaRead
from app.models.partida import EstadosPartida, EstadoPartida, FasePartida, EstadoJugador
from app.api.deps import obtener_usuario_actual
from app.models.usuario import User
from app.db.session import get_db
from app.crud import crud_partidas, crud_combates
from app.crud.crud_logs import obtener_logs

# Cosas nuevas para empezar la partida
from app.core.map_state import game_map_state
from app.core.logica_juego.inicializacion import generar_reparto_inicial, repartir_tropas_iniciales, determinar_orden_jugadores
from app.core.logica_juego.maquina_estados import iniciar_temporizador, tareas_en_segundo_plano, asignar_tropas_reserva, timers_por_partida, votos_pausa

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
    if await crud_partidas.obtener_partida_activa_del_jugador(db, usuario_actual.username):
        raise HTTPException(status_code=400, detail="Ya estás en una partida activa. Termínala o abandónala primero.")

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
    return await crud_partidas.obtener_partidas_publicas(db)

@router.get("/pausadas", response_model=list[PartidaRead])
async def listar_partidas_pausadas(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve todas las partidas en las que el usuario participa y están pausadas.
    """
    return await crud_partidas.obtener_partidas_pausadas_usuario(db, usuario_actual.username)

@router.post("/{codigo}/unirse", response_model=UnirseOut)
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
    
    if await crud_partidas.obtener_partida_activa_del_jugador(db, usuario_actual.username):
        raise HTTPException(status_code=400, detail="Ya estás en otra partida activa. Termínala o abandónala primero.")

    await crud_partidas.unir_jugador(
        db,
        usuario_actual.username,
        partida.id,
        len(jugadores_actuales) + 1,
    )

    await notifier.notificar_nuevo_jugador(
        partida_id=partida.id,
        username=usuario_actual.username,
    )

    jugadores_actualizados = await crud_partidas.obtener_jugadores_partida(db, partida.id)
    
    if len(jugadores_actuales) == 0:
        await crud_partidas.actualizar_creador_partida(db, partida, usuario_actual.username)


    return UnirseOut(
        mensaje="Unido a la partida",
        jugadores_en_sala=jugadores_actualizados,
        creador=partida.creador
    )

@router.post("/{partida_id}/abandonar", response_model=AbandonarOut, status_code=status.HTTP_200_OK)
async def abandonar_partida(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Permite a un usuario abandonar una partida que se encuentra en la sala de espera (fase de creación).

    - **partida_id**: Identificador único de la partida a abandonar.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.

    Retorna un mensaje de confirmación y la lista actualizada de jugadores que permanecen en la sala.
    """
    partida = await crud_partidas.obtener_partida_por_id(db, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if partida.estado != EstadosPartida.CREANDO:
        raise HTTPException(status_code=400, detail="Solo puedes abandonar mientras la partida está en el lobby")

    jugadores = await crud_partidas.obtener_jugadores_partida(db, partida_id)
    if not any(j.usuario_id == usuario_actual.username for j in jugadores):
        raise HTTPException(status_code=400, detail="No estás en esta partida")

    await crud_partidas.eliminar_jugador(db, partida_id, usuario_actual.username)

    # Si el host se va, cerramos la sala
    if partida.creador == usuario_actual.username:
        await notifier.notificar_sala_cerrada(partida_id)
        await crud_partidas.eliminar_partida(db, partida_id)
        return AbandonarOut(mensaje="Has abandonado la partida. La sala ha sido cerrada.")
    else:
        await notifier.notificar_desconexion(partida_id, usuario_actual.username)
        return AbandonarOut(mensaje="Has abandonado la partida")


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

    jugadores = await crud_partidas.obtener_jugadores_partida(db, partida_id)

    if len(jugadores) < 2:
        raise HTTPException(status_code=400, detail="Mínimo 2 jugadores para empezar la partida")


    if partida.creador != usuario_actual.username:
        raise HTTPException(status_code=403, detail="Solo el creador puede empezar")

    jugadores_ids = [j.usuario_id for j in jugadores]
    comarcas_ids = list(game_map_state.comarcas.keys())
    
    mapa_repartido = generar_reparto_inicial(jugadores_ids, comarcas_ids)
    
    repartir_tropas_iniciales(mapa_repartido, jugadores_ids)

    estado_jugadores, jugador_turno_1 = determinar_orden_jugadores(jugadores)


    fin_fase = datetime.now(timezone.utc) + timedelta(seconds=partida.config_timer_seconds)
    
    nuevo_estado = EstadoPartida(
        partida_id=partida.id,
        fase_actual=FasePartida.REFUERZO,
        fin_fase_actual=fin_fase,
        user_turno_actual=jugador_turno_1,
        mapa=mapa_repartido,
        jugadores=estado_jugadores
    )

    await asignar_tropas_reserva(nuevo_estado, db) 

    # Guardamos el inicio de la partida (estado ACTIVA + EstadoPartida)
    await crud_partidas.guardar_inicio_partida(db, partida, nuevo_estado)

    # Le damos al cronómetro invisible y lo metemos en la lista fuerte
    tarea_inicio = asyncio.create_task(iniciar_temporizador(partida.id, FasePartida.REFUERZO, fin_fase))
    tareas_en_segundo_plano.add(tarea_inicio)
    tarea_inicio.add_done_callback(tareas_en_segundo_plano.discard)

    await notifier.enviar_inicio_partida(
        partida_id=partida.id,
        mapa=mapa_repartido,
        jugadores=nuevo_estado.jugadores,
        turno_de=jugador_turno_1,
        fin_fase=fin_fase
    )

    return {
        "mensaje": "¡Aragón está en guerra!", 
        "partida_id": partida.id, 
        "turno_de": jugador_turno_1,
        "fase": "refuerzo"
    }


@router.get("/mi-partida", response_model=PartidaActivaOut, status_code=status.HTTP_200_OK)
async def obtener_mi_partida_activa(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve la partida activa del jugador autenticado, si existe.
    Útil para reconectar tras cerrar la app.
    """
    entrada = await crud_partidas.obtener_partida_activa_del_jugador(db, usuario_actual.username)
    if not entrada:
        return PartidaActivaOut(tiene_partida_activa=False)

    partida = await crud_partidas.obtener_partida_por_id(db, entrada.partida_id)
    estado = await crud_partidas.obtener_estado_partida(db, entrada.partida_id)

    return {
        "tiene_partida_activa": True,
        "partida_id": partida.id,
        "estado": partida.estado,
        "codigo_invitacion": partida.codigo_invitacion,
        "fase_actual": estado.fase_actual if estado else None,
        "turno_de": estado.user_turno_actual if estado else None,
        "fin_fase_utc": estado.fin_fase_actual if estado else None,
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

    partida = await crud_partidas.obtener_partida_por_codigo(db, code)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if partida.estado != EstadosPartida.PAUSADA:
        raise HTTPException(status_code=400, detail="La partida no está pausada")
    if partida.creador != usuario_actual.username:
        raise HTTPException(status_code=403, detail="Solo el host puede reanudar la partida")

    jugadores_vivos = await crud_partidas.obtener_jugadores_vivos(db, partida.id)
    sala_ws = manager.active_connections.get(partida.id, {})
    
    if len(sala_ws) < len(jugadores_vivos):
        raise HTTPException(
            status_code=400, 
            detail=f"Faltan jugadores por conectarse. Hay {len(sala_ws)}/{len(jugadores_vivos)} listos."
        )

    estado = await crud_partidas.obtener_estado_partida(db, partida.id)
    if not estado:
        raise HTTPException(status_code=404, detail="Estado de partida no encontrado")

    votos_pausa.pop(partida.id, None)

    nuevo_fin_fase = datetime.now(timezone.utc) + timedelta(seconds=partida.config_timer_seconds)
    estado.fin_fase_actual = nuevo_fin_fase
    partida.estado = EstadosPartida.ACTIVA
    await db.commit()

    nueva_tarea = asyncio.create_task(
        iniciar_temporizador(partida.id, estado.fase_actual, nuevo_fin_fase)
    )
    timers_por_partida[partida.id] = nueva_tarea
    tareas_en_segundo_plano.add(nueva_tarea)
    nueva_tarea.add_done_callback(tareas_en_segundo_plano.discard)

    await notifier.enviar_partida_reanudada(
        partida_id=partida.id,
        nueva_fase=estado.fase_actual.value,
        jugador_activo=estado.user_turno_actual,
        fin_fase_utc=nuevo_fin_fase.isoformat()
    )

    return AccionPausaOut(
        mensaje="La partida ha sido reanudada.",
        estado_actual=EstadosPartida.ACTIVA.value
    )

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
    partida = await crud_partidas.obtener_partida_por_codigo(db, code)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if partida.estado != EstadosPartida.ACTIVA:
        raise HTTPException(status_code=400, detail="La partida no está activa")

    jugadores = await crud_partidas.obtener_jugadores_partida(db, partida.id)
    if not any(j.usuario_id == usuario_actual.username for j in jugadores):
        raise HTTPException(status_code=403, detail="No eres jugador de esta partida")

    if partida.id in votos_pausa:
        raise HTTPException(status_code=400, detail="Ya hay una votación de pausa en curso")

    votos_pausa[partida.id] = {}

    await notifier.enviar_solicitud_pausa(partida.id, usuario_actual.username)

    return AccionPausaOut(
        mensaje="Votación de pausa iniciada. Todos deben votar a favor para pausar.",
        estado_actual=partida.estado.value
    )


@router.post("/{code}/pausa/votar", response_model=AccionPausaOut, status_code=status.HTTP_200_OK)
async def votar_pausa(
    code: str,
    voto_in: VotoPausa,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Los jugadores usan este endpoint para votar si quieren pausar o no.
    Si los votos a favor alcanzan unanimidad, el estado pasará a PAUSADA.
    Un voto en contra cancela la votación.

    - **code**: Código único de 6 caracteres de la partida.
    - **voto_in**: Booleano indicando si vota que SÍ (true) o que NO (false).
    - **usuario_actual**: El jugador que emite el voto.
    - **db**: Sesión de base de datos asíncrona.
    """
    partida = await crud_partidas.obtener_partida_por_codigo(db, code)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    if partida.estado != EstadosPartida.ACTIVA:
        raise HTTPException(status_code=400, detail="La partida no está activa")

    jugadores = await crud_partidas.obtener_jugadores_partida(db, partida.id)
    if not any(j.usuario_id == usuario_actual.username for j in jugadores):
        raise HTTPException(status_code=403, detail="No eres jugador de esta partida")

    if partida.id not in votos_pausa:
        raise HTTPException(status_code=400, detail="No hay ninguna votación de pausa activa")

    if usuario_actual.username in votos_pausa[partida.id]:
        raise HTTPException(status_code=400, detail="Ya has votado")

    votos_pausa[partida.id][usuario_actual.username] = voto_in.voto_a_favor

    if not voto_in.voto_a_favor:
        del votos_pausa[partida.id]
        await notifier.enviar_pausa_rechazada(partida.id, usuario_actual.username)
        return AccionPausaOut(
            mensaje="Has votado en contra. La pausa ha sido cancelada.",
            estado_actual=partida.estado.value
        )

    jugadores_vivos = [j for j in jugadores if j.estado_jugador == EstadoJugador.VIVO]
    total = len(jugadores_vivos)
    votos_favor = sum(1 for v in votos_pausa[partida.id].values() if v)

    await notifier.enviar_voto_registrado(partida.id, usuario_actual.username, True, votos_favor, total)

    if votos_favor >= total:
        del votos_pausa[partida.id]

        timer = timers_por_partida.pop(partida.id, None)
        if timer and not timer.done():
            timer.cancel()

        partida.estado = EstadosPartida.PAUSADA
        await db.commit()

        await notifier.enviar_partida_pausada(partida.id)
        return AccionPausaOut(
            mensaje="¡Unanimidad! La partida ha sido pausada.",
            estado_actual=EstadosPartida.PAUSADA.value
        )

    return AccionPausaOut(
        mensaje=f"Voto registrado ({votos_favor}/{total} a favor).",
        estado_actual=partida.estado.value
    )

@router.post("/{partida_id}/fortificar", status_code=status.HTTP_200_OK)
async def fortificar_tropas(
    partida_id: int,
    datos: FortificarIn,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Fase final del turno: Permite redistribuir tropas aliadas entre dos territorios adyacentes.
    """
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)
    if not estado:
        raise HTTPException(status_code=404, detail="Estado de partida no encontrado")

    t_origen = estado.mapa.get(datos.origen)
    t_destino = estado.mapa.get(datos.destino)

    if not t_origen or not t_destino:
        raise HTTPException(status_code=400, detail="Territorio de origen o destino no existe en el mapa")

    try:
        validar_fortificacion(
            estado_partida=estado,
            jugador_id=usuario_actual.username,
            origen_id=datos.origen,
            t_origen=TerritorioBase(**t_origen),
            destino_id=datos.destino,
            t_destino=TerritorioBase(**t_destino),
            tropas_a_mover=datos.tropas,
            grafo_aragon=map_calculator
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    es_conquista_neutral = estado.mapa[datos.destino].get("owner_id") == "neutral"

    resolver_fortificacion(estado.mapa, datos.origen, datos.destino, datos.tropas)
    
    if es_conquista_neutral:
        estado.mapa[datos.destino]["owner_id"] = usuario_actual.username
        flag_modified(estado, "mapa")

    estado.jugadores[usuario_actual.username]["ha_fortificado"] = True
    flag_modified(estado, "jugadores")
    
    await crud_combates.guardar_estado_partida(db, estado)

    await notifier.enviar_movimiento_conquista(
        partida_id=partida_id,
        origen_id=datos.origen,
        destino_id=datos.destino,
        tropas=datos.tropas,
        jugador_id=usuario_actual.username
    )

    if es_conquista_neutral:
        await notifier.enviar_actualizacion_territorio(
            partida_id=partida_id,
            territorio_id=datos.destino,
            data_territorio=estado.mapa[datos.destino]
        )

    return {
        "mensaje": "Fortificación completada",
        "origen": datos.origen,
        "destino": datos.destino,
        "tropas": datos.tropas
    }

@router.post("/{partida_id}/trabajar")
async def asignar_trabajo(partida_id: int, datos: AsignarTrabajoIn, usuario_actual: User = Depends(obtener_usuario_actual), db: AsyncSession = Depends(get_db)):
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    t_destino = obtener_datos_territorio(estado.mapa, datos.territorio_id)

    try:
        validar_asignar_trabajo(estado, jugador_id, datos.territorio_id, t_destino)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Aplicamos el bloqueo
    t_destino.estado_bloqueo = "trabajando"
    estado.jugadores[jugador_id]["territorio_trabajando"] = datos.territorio_id
    estado.mapa[datos.territorio_id] = t_destino.model_dump()

    flag_modified(estado, "jugadores")
    flag_modified(estado, "mapa")
    await db.commit()

    await notifier.enviar_actualizacion_territorio(partida_id, datos.territorio_id, estado.mapa[datos.territorio_id])

    return {"mensaje": f"El territorio {datos.territorio_id} se ha puesto a trabajar."}

@router.post("/{partida_id}/investigar")
async def asignar_investigacion(partida_id: int, datos: AsignarInvestigacionIn, usuario_actual: User = Depends(obtener_usuario_actual), db: AsyncSession = Depends(get_db)):
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    t_destino = obtener_datos_territorio(estado.mapa, datos.territorio_id)

    try:
        validar_asignar_investigacion(estado, jugador_id, t_destino, datos.habilidad_id )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Aplicamos el bloqueo
    t_destino.estado_bloqueo = "investigando"
    estado.jugadores[jugador_id]["territorio_investigando"] = datos.territorio_id
    estado.jugadores[jugador_id]["habilidad_investigando"] = datos.habilidad_id
    estado.mapa[datos.territorio_id] = t_destino.model_dump()

    flag_modified(estado, "jugadores")
    flag_modified(estado, "mapa")
    await db.commit()

    await notifier.enviar_actualizacion_territorio(partida_id, datos.territorio_id, estado.mapa[datos.territorio_id])

    return {"mensaje": f"El territorio {datos.territorio_id} está investigando {datos.habilidad_id}."}

@router.post("/{partida_id}/comprar_tecnologia")
async def comprar_tecnologia(partida_id: int, datos: ComprarTecnologiaIn, usuario_actual: User = Depends(obtener_usuario_actual), db: AsyncSession = Depends(get_db)):
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)
    jugador_id = usuario_actual.username
    jugador = estado.jugadores.get(jugador_id)

    if not jugador:
        raise HTTPException(404, "Jugador no encontrado")

    if estado.fase_actual.value != "ataque_especial":
        raise HTTPException(400, "Solo puedes comprar tecnologías en la fase de ataque especial.")

    tech_id = datos.tecnologia_id
    if tech_id not in HABILIDADES:
        raise HTTPException(400, f"La tecnología '{tech_id}' no existe.")

    # Validaciones de compra
    if tech_id not in jugador.get("tecnologias_predesbloqueadas", []):
        raise HTTPException(400, "No tienes esta tecnología predesbloqueada.")

    if tech_id in jugador.get("tecnologias_compradas", []):
        raise HTTPException(400, "Ya has comprado esta tecnología.")

    precio = HABILIDADES.get(tech_id, {}).get("precio")
    if not precio:
        raise HTTPException(400, "Tecnología no válida.")

    if jugador.get("monedas", 0) < precio:
        raise HTTPException(400, f"Monedas insuficientes. Necesitas {precio} y tienes {jugador.get('monedas')}.")

    # Ejecutar compra
    jugador["monedas"] -= precio
    jugador["tecnologias_compradas"].append(tech_id)

    flag_modified(estado, "jugadores")
    await db.commit()

    return {"mensaje": f"Has adquirido {tech_id} con éxito. Te quedan {jugador['monedas']} monedas."}

@router.get("/{partida_id}/tecnologias", response_model=TecnologiasPartidaOut)
async def obtener_tecnologias_partida(
    partida_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    estado = await crud_partidas.obtener_estado_partida(db, partida_id)
    if not estado:
        raise HTTPException(404, "Partida no encontrada o aún no iniciada.")
    
    jugador_id  = usuario_actual.username
    jugador = estado.jugadores.get(jugador_id)
    if not jugador:
        raise HTTPException(404, "Jugador no encontrado en esta partida.")

    predesbloqueadas = jugador.get("tecnologias_predesbloqueadas", [])
    compradas = jugador.get("tecnologias_compradas", [])

    resultado: dict[str, list] = {}
    for habilidad_id, nodo in ARBOL_TECNOLOGICO.items():
        info = HABILIDADES[habilidad_id]
        rama = info["rama"]
        if rama not in resultado:
            resultado[rama] = []
        cfg_ataque = CONFIG_ATAQUES.get(habilidad_id, {})
        resultado[rama].append(HabilidadOut(
            id=habilidad_id,
            nombre=info["nombre"],
            descripcion=info["descripcion"],
            nivel=info["nivel"],
            prerequisito=nodo["prerequisito"],
            desbloquea=nodo["desbloquea"],
            precio=info["precio"],
            predesbloqueada=habilidad_id in predesbloqueadas,
            comprada=habilidad_id in compradas,
            rango=cfg_ataque.get("rango"),
        ))

    return TecnologiasPartidaOut(ramas=resultado)

@router.get("/{partida_id}/logs", response_model=list[LogPartidaRead], status_code=status.HTTP_200_OK)
async def obtener_logs_partida(
    partida_id: int,
    limit: int = 50,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve el historial de eventos de una partida, más recientes primero.
    """
    return await obtener_logs(db, partida_id, limit)