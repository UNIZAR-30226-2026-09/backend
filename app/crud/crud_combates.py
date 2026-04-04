from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.partida import EstadoPartida, JugadoresPartida, EstadoJugador, Partida, EstadosPartida
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
# 2. VERIFICAR Y ELIMINAR JUGADOR (CON FINALIZACIÓN DE PARTIDA)
# ----------------------------------------------------------------------------
async def verificar_eliminacion_jugador(db: AsyncSession, partida_id: int, defensor_id: str, mapa_actualizado: dict) -> bool:
    """
    Comprueba si un jugador se ha quedado sin territorios tras un ataque.
    Si es así, cambia su estado a MUERTO en la base de datos.
    Si solo queda un jugador vivo, finaliza la partida.
    
    Retorna True si el jugador ha sido eliminado, False en caso contrario.
    """
    territorios_restantes = obtener_territorios_jugador(mapa_actualizado, defensor_id)
    
    if len(territorios_restantes) == 0:
        # El jugador ha perdido todo, lo buscamos
        query = select(JugadoresPartida).where(
            JugadoresPartida.partida_id == partida_id,
            JugadoresPartida.usuario_id == defensor_id
        )
        resultado = await db.execute(query)
        jugador_bd = resultado.scalar_one_or_none()
        
        if jugador_bd and jugador_bd.estado_jugador == EstadoJugador.VIVO:

            jugador_bd.estado_jugador = EstadoJugador.MUERTO
            await db.commit()

            # Contamos cuántos vivos quedan
            query_vivos = select(JugadoresPartida).where(
                JugadoresPartida.partida_id == partida_id,
                JugadoresPartida.estado_jugador == EstadoJugador.VIVO
            )
            resultado_vivos = await db.execute(query_vivos)
            jugadores_vivos = resultado_vivos.scalars().all()

            # Si solo queda 1 jugador vivo, la partida ha terminado
            if len(jugadores_vivos) == 1:
                ganador_id = jugadores_vivos[0].usuario_id
                
                # Buscamos la partida y la finalizamos
                query_partida = select(Partida).where(Partida.id == partida_id)
                res_partida = await db.execute(query_partida)
                partida_bd = res_partida.scalar_one_or_none()
                
                if partida_bd:
                    partida_bd.estado = EstadosPartida.FINALIZADA
                    partida_bd.ganador = ganador_id
                    await db.commit()
            # ---------------------------------------------------

            return True 
            
    return False