from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_combates
from app.crud.crud_partidas import verificar_y_finalizar_partida
from app.crud.crud_logs import registrar_log
from app.core.notifier import notifier


async def resolver_eliminaciones(
    db: AsyncSession,
    partida_id: int,
    defensores: set[str],
    mapa: dict,
    turno_actual: int,
    fase_actual: str,
    atacante_id: str | None = None,
) -> str | None:
    """
    Para cada defensor potencial comprueba si se ha quedado sin territorios.
    Si es eliminado: notifica por WS, registra log y comprueba fin de partida.
    Devuelve el username del ganador si la partida ha terminado, None si continúa.
    atacante_id es None cuando la eliminación viene de un efecto (tick de enfermedad).
    """
    for defensor_id in defensores:
        eliminado = await crud_combates.verificar_eliminacion_jugador(
            db=db,
            partida_id=partida_id,
            defensor_id=defensor_id,
            mapa_actualizado=mapa,
        )
        if not eliminado:
            continue

        await notifier.enviar_jugador_eliminado(partida_id, defensor_id)
        await registrar_log(
            db=db,
            partida_id=partida_id,
            turno_numero=turno_actual,
            fase=fase_actual,
            tipo_evento="JUGADOR_ELIMINADO",
            user=atacante_id or defensor_id,
            datos={"eliminado": defensor_id, "por_quien": atacante_id},
        )

        ganador = await verificar_y_finalizar_partida(db, partida_id)
        if ganador:
            await notifier.enviar_fin_partida(partida_id, ganador)
            await registrar_log(
                db=db,
                partida_id=partida_id,
                turno_numero=turno_actual,
                fase=fase_actual,
                tipo_evento="PARTIDA_FINALIZADA",
                user=ganador,
                datos={"ganador": ganador},
            )
            return ganador

    return None
