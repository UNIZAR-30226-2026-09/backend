import random
from app.schemas.estado_juego import TerritorioBase
from app.core.logica_juego.utils import obtener_territorios_jugador


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
        units=1
    )
    
    return territorio.model_dump()


def generar_reparto_inicial(jugadores_ids: list[str], comarcas: list[str]) -> dict:
    comarcas_barajadas = barajar_comarcas(comarcas)
    mapa = {}

    for i, comarca_id in enumerate(comarcas_barajadas):
        owner = obtener_owner(jugadores_ids, i)
        mapa[comarca_id] = crear_estado_comarca(owner)

    return mapa

def repartir_tropas_iniciales(mapa: dict, jugadores_ids: list[str]) -> None:
    """
    Reparte tropas extra aleatoriamente sobre los territorios de cada jugador.
    Cada jugador recibe tantas tropas extra como territorios tiene
    """
    for jugador_id in jugadores_ids:
        
        territorios_jugador = obtener_territorios_jugador(mapa, jugador_id)
        
        # Por cada territorio, elegimos uno random y le añadimos 1
        for _ in range(len(territorios_jugador)):
            territorio_elegido = random.choice(territorios_jugador)
            mapa[territorio_elegido]["units"] += 1


def determinar_orden_jugadores(jugadores):
    """
    Asigna un orden aleatorio a los jugadores einicializa sus estados
    """

    numeros = list(range(1, len(jugadores) + 1))
    random.shuffle(numeros)
    
    estado_jugadores = {}
    jugador_turno_1 = None
    
    for i, j in enumerate(jugadores):
        j.turno = numeros[i]
        estado_jugadores[j.usuario_id] = {
            "numero_jugador": j.turno,
            "tropas_reserva": 0,
            "movimiento_conquista_pendiente": False,
            "origen_conquista": None,
            "destino_conquista": None,
            "ha_fortificado": False
        }
        
        if j.turno == 1:
            jugador_turno_1 = j.usuario_id
            
    return estado_jugadores, jugador_turno_1