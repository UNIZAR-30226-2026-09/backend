import random
from app.schemas.estado_juego import TerritorioBase

def barajar_comarcas(comarcas: list[str]) -> list[str]:
    comarcas_barajadas = comarcas.copy()
    random.shuffle(comarcas_barajadas)
    return comarcas_barajadas


def obtener_owner(jugadores_ids: list[str], indice: int) -> str:
    return jugadores_ids[indice % len(jugadores_ids)]


def crear_estado_comarca(owner_id: str) -> dict:
    
    # Usamos el schema del JSONB mapa 
    territorio = TerritorioBase(
        owner_id=owner_id, 
        units=random.randint(3, 5)
    )
    
    return territorio.model_dump()


def generar_reparto_inicial(jugadores_ids: list[str], comarcas: list[str]) -> dict:
    comarcas_barajadas = barajar_comarcas(comarcas)
    mapa = {}

    for i, comarca_id in enumerate(comarcas_barajadas):
        owner = obtener_owner(jugadores_ids, i)
        mapa[comarca_id] = crear_estado_comarca(owner)

    return mapa