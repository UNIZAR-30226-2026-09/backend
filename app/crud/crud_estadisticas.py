from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.usuario import Estadistica

async def inicializar_estadisticas(db: AsyncSession, nombre_user: str) -> Estadistica:
    stats = Estadistica(nombre_user=nombre_user, conquistas_por_region={})
    db.add(stats)
    await db.commit()
    await db.refresh(stats)
    return stats

async def obtener_estadisticas(db: AsyncSession, nombre_user: str) -> Estadistica | None:
    query = select(Estadistica).where(Estadistica.nombre_user == nombre_user)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def obtener_ranking_global(db: AsyncSession, limite: int = 10) -> list[Estadistica]:
    query = select(Estadistica).order_by(
        desc(Estadistica.num_partidas_ganadas),
        desc(Estadistica.num_soldados_matados)
    ).limit(limite)
    result = await db.execute(query)
    return result.scalars().all()

async def registrar_fin_partida(
    db: AsyncSession, 
    nombre_user: str, 
    es_ganador: bool, 
    regiones_conquistadas: dict[str, int] = None,
    soldados_matados_en_partida: int = 0
) -> Estadistica:
    
    stats = await obtener_estadisticas(db, nombre_user)
    if not stats:
        stats = await inicializar_estadisticas(db, nombre_user)

    stats.num_partidas_jugadas += 1
    stats.num_soldados_matados += soldados_matados_en_partida
    
    if es_ganador:
        stats.num_partidas_ganadas += 1

    if regiones_conquistadas:
        stats.num_regiones_conquistadas += sum(regiones_conquistadas.values())
        
        nuevo_historial = dict(stats.conquistas_por_region or {})
        for region, cantidad in regiones_conquistadas.items():
            nuevo_historial[region] = nuevo_historial.get(region, 0) + cantidad
            
        stats.conquistas_por_region = nuevo_historial

    await db.commit()
    await db.refresh(stats)
    return stats