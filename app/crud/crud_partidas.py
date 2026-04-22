from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional

from app.models.partida import (
    Partida,
    JugadoresPartida,
    EstadoPartida,
    EstadosPartida,
    TipoVisibilidad,
    EstadoJugador
)
from app.schemas.partida import PartidaCreate


# ----------------------------------------------------------------------------
# 1. CREAR PARTIDA Y CREADOR
# ----------------------------------------------------------------------------
async def crear_partida_y_creador(
    db: AsyncSession, 
    partida_in: PartidaCreate, 
    codigo: str, 
    creador_username: str
) -> Partida:
    """
    Crea una nueva partida, hace commit, luego crea el JugadoresPartida 
    (turno 1, ColorJugador.ROJO), hace commit y devuelve la partida.
    
    Args:
        db: Sesión de base de datos
        partida_in: Datos de configuración de la partida
        codigo: Código de invitación generado
        creador_username: Username del usuario creador
        
    Returns:
        Objeto Partida creado y refrescado
    """
    nueva_partida = Partida(
        config_max_players=partida_in.config_max_players,
        config_visibility=partida_in.config_visibility,
        config_timer_seconds=partida_in.config_timer_seconds,
        codigo_invitacion=codigo,
        estado=EstadosPartida.CREANDO,
        creador=creador_username
    )
    
    db.add(nueva_partida)
    await db.commit()
    await db.refresh(nueva_partida)
    
    creador = JugadoresPartida(
        usuario_id=creador_username,
        partida_id=nueva_partida.id,
        turno=1,
    )
    db.add(creador)
    await db.commit()
    
    return nueva_partida

# ----------------------------------------------------------------------------
# 2. OBTENER PARTIDAS PÚBLICAS
# ----------------------------------------------------------------------------
async def obtener_partidas_publicas(db: AsyncSession) -> list[Partida]:
    """
    Devuelve la lista de partidas en estado CREANDO y visibilidad PUBLICA.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de partidas públicas disponibles
    """
    query = select(Partida).where(
        Partida.estado == EstadosPartida.CREANDO,
        Partida.config_visibility == TipoVisibilidad.PUBLICA
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 3. OBTENER PARTIDA POR CÓDIGO
# ----------------------------------------------------------------------------
async def obtener_partida_por_codigo(db: AsyncSession, codigo: str) -> Optional[Partida]:
    """
    Busca una partida por su código de invitación.
    
    Args:
        db: Sesión de base de datos
        codigo: Código de invitación de la partida
        
    Returns:
        Objeto Partida si existe, None en caso contrario
    """
    query = select(Partida).where(Partida.codigo_invitacion == codigo)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 4. OBTENER PARTIDA POR ID
# ----------------------------------------------------------------------------
async def obtener_partida_por_id(db: AsyncSession, partida_id: int) -> Optional[Partida]:
    """
    Busca una partida por su ID.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Objeto Partida si existe, None en caso contrario
    """
    query = select(Partida).where(Partida.id == partida_id)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 5. OBTENER JUGADORES DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def obtener_jugadores_partida(db: AsyncSession, partida_id: int) -> list[JugadoresPartida]:
    """
    Devuelve la lista de jugadores de una partida, ordenados por turno ascendente.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Lista de jugadores ordenados por turno
    """
    query = select(JugadoresPartida).where(
        JugadoresPartida.partida_id == partida_id
    ).order_by(JugadoresPartida.turno.asc())
    
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 6. UNIR JUGADOR A PARTIDA
# ----------------------------------------------------------------------------
async def unir_jugador(
    db: AsyncSession,
    username: str,
    partida_id: int,
    turno: int,
) -> JugadoresPartida:
    nuevo_jugador = JugadoresPartida(
        usuario_id=username,
        partida_id=partida_id,
        turno=turno,
    )

    db.add(nuevo_jugador)
    await db.commit()
    await db.refresh(nuevo_jugador)

    return nuevo_jugador

# ----------------------------------------------------------------------------
# 7. GUARDAR INICIO DE PARTIDA
# ----------------------------------------------------------------------------
async def guardar_inicio_partida(
    db: AsyncSession, 
    partida: Partida, 
    estado_tablero: EstadoPartida
) -> None:
    """
    Actualiza el estado de la partida a ACTIVA, añade el estado_tablero 
    a la base de datos y hace el commit.
    
    Args:
        db: Sesión de base de datos
        partida: Objeto Partida a actualizar
        estado_tablero: EstadoPartida a crear
        
    Returns:
        None
    """
    partida.estado = EstadosPartida.ACTIVA
    db.add(estado_tablero)
    await db.commit()

# ----------------------------------------------------------------------------
# 8. OBTENER ESTADO DE UNA PARTIDA
# ----------------------------------------------------------------------------
async def obtener_estado_partida(db: AsyncSession, partida_id: int) -> Optional[EstadoPartida]:
    """
    Busca el EstadoPartida por su partida_id.
    
    Args:
        db: Sesión de base de datos
        partida_id: ID de la partida
        
    Returns:
        Objeto EstadoPartida si existe, None en caso contrario
    """
    query = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()


# ----------------------------------------------------------------------------
# 8. Eliminar a un judador de la partida
# ----------------------------
async def eliminar_jugador(db: AsyncSession, partida_id: int, username: str) -> None:
    await db.execute(
        delete(JugadoresPartida).where(
            JugadoresPartida.partida_id == partida_id,
            JugadoresPartida.usuario_id == username
        )
    )
    await db.commit()

# ----------------------------------------------------------------------------
# 9. OBTENER PARTIDA ACTIVA DEL JUGADOR
# ----------------------------------------------------------------------------
async def obtener_partida_activa_del_jugador(
    db: AsyncSession, username: str
) -> Optional[JugadoresPartida]:
    """
    Comprueba si un usuario ya pertenece a una partida que no ha terminado.
    
    Args:
        db: Sesión de base de datos
        username: Username del jugador
        
    Returns:
        Objeto JugadoresPartida si está en una partida activa, None en caso contrario
    """
    query = (
        select(JugadoresPartida)
        .join(Partida, JugadoresPartida.partida_id == Partida.id)
        .where(
            JugadoresPartida.usuario_id == username,
            Partida.estado.in_([
                EstadosPartida.CREANDO,
                EstadosPartida.ACTIVA,
                EstadosPartida.PAUSADA,
            ])
        )
    )
    resultado = await db.execute(query)
    return resultado.scalars().first()

# ----------------------------------------------------------------------------
# 10. Actualizar tropas reserva
# ----------------------------------------------------------------------------
async def actualizar_tropas_reserva(db: AsyncSession, estado: EstadoPartida, usuario_id: str,
      cantidad: int) -> None:
    """
        Actualiza el saldo de tropas en el JSONB 'jugadores' del EstadoPartida.
    """

    if usuario_id not in estado.jugadores:
        # Si el jugador no existe (raro), lo inicializamos con valores base
        estado.jugadores[usuario_id] = {
            "numero_jugador": 0,
            "tropas_reserva": 0,
            "movimiento_conquista_pendiente": False
        }
    
    # Obtenemos el saldo actual de forma segura (fallback a 0)
    actual = estado.jugadores[usuario_id].get("tropas_reserva", 0)
    estado.jugadores[usuario_id]["tropas_reserva"] = actual + cantidad
    
    flag_modified(estado, "jugadores")


# ----------------------------------------------------------------------------
# 11. OBTENER JUGADORES VIVOS
# ----------------------------------------------------------------------------
async def obtener_jugadores_vivos(db: AsyncSession, partida_id: int) -> list[JugadoresPartida]:
    """
    Devuelve la lista de jugadores que siguen vivos en una partida específica.
    """

    query = select(JugadoresPartida).where(
        JugadoresPartida.partida_id == partida_id,
        JugadoresPartida.estado_jugador == EstadoJugador.VIVO
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 12. VERIFICAR Y FINALIZAR PARTIDA SI HAY UN SOLO GANADOR
# ----------------------------------------------------------------------------
async def verificar_y_finalizar_partida(db: AsyncSession, partida_id: int) -> Optional[str]:
    """
    Comprueba cuántos jugadores siguen vivos en la partida.
    Si solo queda uno, finaliza la partida y lo establece como ganador.
    Retorna el username del ganador o None si el juego continúa.
    """
    jugadores_vivos = await obtener_jugadores_vivos(db, partida_id)

    # Solo un jugador, hay que terminar la partida
    if len(jugadores_vivos) == 1:
        ganador_username = jugadores_vivos[0].usuario_id
        partida = await obtener_partida_por_id(db, partida_id)

        if partida:
            partida.estado = EstadosPartida.FINALIZADA
            partida.ganador = ganador_username
            
            # --- TAREA 19: REGISTRAR ESTADÍSTICAS HISTÓRICAS ---
            from app.crud import crud_estadisticas
            
            # Obtenemos el estado para sacar los datos de la partida
            estado = await obtener_estado_partida(db, partida_id)
            # Obtenemos todos los que participaron (vivos y muertos)
            todos_los_participantes = await obtener_jugadores_partida(db, partida_id)
            
            for p in todos_los_participantes:
                es_ganador = (p.usuario_id == ganador_username)
                
                # Extraemos los datos acumulados en el JSON de la partida
                datos_partida = estado.jugadores.get(p.usuario_id, {}) if estado else {}
                
                # vas sumando estos valores al JSON 'jugadores' del estado.
                regiones = datos_partida.get("historial_conquistas", {}) 
                bajas = datos_partida.get("bajas_causadas", 0)

                await crud_estadisticas.registrar_fin_partida(
                    db=db,
                    nombre_user=p.usuario_id,
                    es_ganador=es_ganador,
                    regiones_conquistadas=regiones,
                    soldados_matados_en_partida=bajas
                )
            # ---------------------------------------------------
            
            await db.commit()
            
        return ganador_username

    # Hay más de un jugador, la partida sigue
    return None

# ----------------------------------------------------------------------------
# 13. ACTUALIZAR CREADOR DE LA PARTIDA
# ----------------------------------------------------------------------------
async def actualizar_creador_partida(
    db: AsyncSession, 
    partida: Partida, 
    nuevo_creador_username: str
) -> None:
    """
    Cambia el creador (host) de una partida existente.
    """
    partida.creador = nuevo_creador_username
    await db.commit()


# ----------------------------------------------------------------------------
# 13. ELIMINAR PARTIDA
# ----------------------------------------------------------------------------
async def eliminar_partida(db: AsyncSession, partida_id: int) -> None:
    await db.execute(delete(Partida).where(Partida.id == partida_id))
    await db.commit()