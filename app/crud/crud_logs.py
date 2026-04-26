from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.partida import LogPartida


async def registrar_log(
    db: AsyncSession,
    partida_id: int,
    turno_numero: int,
    fase: str,
    tipo_evento: str,
    user: str | None,
    datos: dict,
) -> None:
    log = LogPartida(
        partida_id=partida_id,
        turno_numero=turno_numero,
        fase=fase,
        tipo_evento=tipo_evento,
        user=user,
        datos=datos,
    )
    db.add(log)
    await db.commit()


async def obtener_logs(db: AsyncSession, partida_id: int, limit: int = 50) -> list[LogPartida]:
    result = await db.execute(
        select(LogPartida)
        .where(LogPartida.partida_id == partida_id)
        .order_by(LogPartida.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()