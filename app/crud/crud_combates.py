from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.partida import EstadoPartida, JugadoresPartida, EstadoJugador
from app.core.logica_juego.utils import obtener_territorios_jugador

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

# ----------------------------------------------------------------------------
# 2. VERIFICAR Y ELIMINAR JUGADOR
# ----------------------------------------------------------------------------
async def verificar_eliminacion_jugador(db: AsyncSession, partida_id: int, defensor_id: str, mapa_actualizado: dict) -> bool:
    """
    Comprueba si un jugador se ha quedado sin territorios tras un ataque.
    Si es así, cambia su estado a MUERTO en la base de datos.
    
    Retorna True si el jugador ha sido eliminado, False en caso contrario.
    """

    territorios_restantes = obtener_territorios_jugador(mapa_actualizado, defensor_id)
    
    if len(territorios_restantes) == 0:

        query_estado = select(EstadoPartida).where(EstadoPartida.partida_id == partida_id)
        resultado_estado = await db.execute(query_estado)
        estado = resultado_estado.scalar_one_or_none()

        if estado:
            atacante_id = estado.user_turno_actual
            jugadores = estado.jugadores
            
            perdedor = jugadores.get(defensor_id, {})
            monedas_saqueadas = perdedor.get("monedas", 0)
            
            if monedas_saqueadas > 0:
                atacante = jugadores.get(atacante_id, {})
                
                # Transferimos los fondos
                atacante["monedas"] = atacante.get("monedas", 0) + monedas_saqueadas
                perdedor["monedas"] = 0
                
                # Guardamos en el diccionario
                jugadores[defensor_id] = perdedor
                jugadores[atacante_id] = atacante
                estado.jugadores = jugadores
                
                # Avisamos a SQLAlchemy de que el JSON ha cambiado
                flag_modified(estado, "jugadores")

        # El jugador ha perdido todo, lo buscamos en la tabla JugadoresPartida
        query = select(JugadoresPartida).where(
            JugadoresPartida.partida_id == partida_id,
            JugadoresPartida.usuario_id == defensor_id
        )
        resultado = await db.execute(query)
        jugador_bd = resultado.scalar_one_or_none()
        
        if jugador_bd and jugador_bd.estado_jugador == EstadoJugador.VIVO:
            
            jugador_bd.estado_jugador = EstadoJugador.MUERTO
            await db.commit()
            return True # Confirmamos que ha sido eliminado
            
    return False