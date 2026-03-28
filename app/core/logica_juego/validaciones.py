# app/core/logica_juego/validaciones.py
from enum import Enum
from app.schemas.estado_juego import TerritorioBase
from app.models.partida import FasePartida

def validar_turno(jugador_actual: str, jugador_id: str):
    if jugador_actual != jugador_id:
        raise ValueError("No es tu turno.")

def validar_fase(fase_actual: FasePartida, fase_permitida: FasePartida):
    if fase_actual != fase_permitida:
        raise ValueError(f"No puedes actuar en la fase {fase_actual.value}.")

def validar_propiedad_territorio(territorio: TerritorioBase, jugador_id: str, rol: str):
    if territorio.owner_id != jugador_id:
        raise ValueError(f"El territorio de {rol} no te pertenece.")

def validar_ataque_no_propio(t_origen: TerritorioBase, t_destino: TerritorioBase):
    if t_origen.owner_id == t_destino.owner_id:
        raise ValueError("No puedes atacarte a ti mismo.")

def validar_tropas(tropas_a_mover: int, tropas_disponibles: int):
    if tropas_a_mover < 1:
        raise ValueError("Debes mover al menos una tropa.")
    if tropas_a_mover > tropas_disponibles:
        raise ValueError("No tienes suficientes tropas libres.")
    if tropas_disponibles - tropas_a_mover < 1:
        raise ValueError("Debes dejar al menos 1 tropa libre en el territorio de origen.")

def validar_ataque_convencional(
    estado_partida,
    origen_id: str,
    t_origen: TerritorioBase,
    destino_id: str,
    t_destino: TerritorioBase,
    tropas_a_mover: int,
    jugador_id: str,
    grafo_aragon
):
    validar_turno(estado_partida.user_turno_actual, jugador_id)
    validar_fase(estado_partida.fase_actual, FasePartida.ATAQUE_CONVENCIONAL)
    
    if not grafo_aragon.son_vecinas(origen_id, destino_id):
        raise ValueError("Los territorios no están conectados.")
    
    validar_propiedad_territorio(t_origen, jugador_id, "origen")
    validar_ataque_no_propio(t_origen, t_destino)
    validar_tropas(tropas_a_mover, t_origen.units)
    
    return True

def validar_colocacion_tropas(estado_partida, jugador_id: str, territorio_id: str, t_destino, tropas_a_poner: int, tropas_reserva: int):
    # ¿Es su turno?
    if estado_partida.user_turno_actual != jugador_id:
        raise ValueError("Quieto ahí, que no es tu turno")
        
    # ¿Está en la fase correcta?
    if estado_partida.fase_actual.value != "refuerzo":
        raise ValueError("Ahora no toca poner tropas, estás en otra fase")

    # ¿El territorio es suyo?
    if t_destino.owner_id != jugador_id:
        raise ValueError("No puedes poner tropas en un territorio enemigo")

    # ¿Tiene pasta (tropas) suficiente?
    if tropas_reserva < tropas_a_poner:
        raise ValueError(f"Solo tienes {tropas_reserva} tropas de reserva")
    

def validar_fortificacion(
    estado_partida,
    jugador_id: str,
    origen_id: str,
    t_origen,
    destino_id: str,
    t_destino,
    tropas_a_mover: int,
    grafo_aragon
):
    # Es mi turno, estoy en la fase correcta y soy el propietario ¿?
    validar_turno(estado_partida.user_turno_actual, jugador_id)
    validar_fase(estado_partida.fase_actual, FasePartida.FORTIFICACION) 

    validar_propiedad_territorio(t_origen, jugador_id, "origen")
    validar_propiedad_territorio(t_destino, jugador_id, "destino")
        
    #! A evolucionar (pueden no estar conectadas pero haber camino)
    if not grafo_aragon.son_vecinas(origen_id, destino_id):
        raise ValueError("Los territorios no están conectados directamente.")
        
    validar_tropas(tropas_a_mover, t_origen.units)
    
    return True