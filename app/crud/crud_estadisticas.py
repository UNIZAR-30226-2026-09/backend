from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_, and_
from sqlalchemy.orm import selectinload
from app.models.usuario import Estadistica

async def inicializar_estadisticas(db: AsyncSession, nombre_user: str) -> Estadistica:
    stats = Estadistica(nombre_user=nombre_user, conquistas_por_comarca={})
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats

async def obtener_estadisticas(db: AsyncSession, nombre_user: str) -> Estadistica | None:
    query = select(Estadistica).where(Estadistica.nombre_user == nombre_user)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def obtener_ranking_global(db: AsyncSession, limite: int = 10) -> list[Estadistica]:
    query = select(Estadistica).options(selectinload(Estadistica.usuario)).order_by(
        desc(Estadistica.num_partidas_ganadas),
        desc(Estadistica.num_soldados_matados)
    ).limit(limite)
    result = await db.execute(query)
    return result.scalars().all()

async def registrar_fin_partida(
    db: AsyncSession,
    nombre_user: str,
    es_ganador: bool,
    comarcas_conquistadas: dict[str, int] = None,
    regiones_dominadas: list[str] = None,
    soldados_matados_en_partida: int = 0
) -> Estadistica:

    stats = await obtener_estadisticas(db, nombre_user)
    if not stats:
        stats = await inicializar_estadisticas(db, nombre_user)

    stats.num_partidas_jugadas += 1
    stats.num_soldados_matados += soldados_matados_en_partida

    if es_ganador:
        stats.num_partidas_ganadas += 1

    if comarcas_conquistadas:
        stats.num_comarcas_conquistadas += sum(comarcas_conquistadas.values())

        nuevo_historial = dict(stats.conquistas_por_comarca or {})
        for comarca, cantidad in comarcas_conquistadas.items():
            nuevo_historial[comarca] = nuevo_historial.get(comarca, 0) + cantidad

        stats.conquistas_por_comarca = nuevo_historial

    if regiones_dominadas:
        stats.num_regiones_conquistadas += len(set(regiones_dominadas))

    await db.commit()
    await db.refresh(stats)
    return stats


async def obtener_posicion_ranking(db: AsyncSession, nombre_user: str) -> int | None:
    stats = await obtener_estadisticas(db, nombre_user)
    if not stats:
        return None

    # Tu posicion en el ranking, cuantos jugadores con más victorias hay!
    query = select(func.count()).select_from(Estadistica).where(
        or_(
            Estadistica.num_partidas_ganadas > stats.num_partidas_ganadas,
            and_(
                Estadistica.num_partidas_ganadas == stats.num_partidas_ganadas,
                Estadistica.num_soldados_matados > stats.num_soldados_matados
            )
        )
    )
    result = await db.execute(query)
    return result.scalar() + 1