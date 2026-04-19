# app/core/logica_juego/validaciones.py
from enum import Enum
from app.schemas.estado_juego import TerritorioBase
from app.models.partida import FasePartida
from app.core.logica_juego.utils import obtener_territorios_jugador

from app.core.logica_juego.config_ataques_especiales import TipoEfecto


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
    

def _territorio_tiene_inhibidor(territorio) -> bool:
    efectos = territorio.efectos if hasattr(territorio, "efectos") else territorio.get("efectos", [])
    for e in efectos:
        tipo = e.tipo_efecto if hasattr(e, "tipo_efecto") else e.get("tipo_efecto")
        if tipo == TipoEfecto.INHIBIDOR_SENAL:
            return True
    return False

def _ataque_bloqueado_por_muro(t_origen, destino_id: str) -> bool:
    efectos = t_origen.efectos if hasattr(t_origen, "efectos") else t_origen.get("efectos", [])
    for e in efectos:
        tipo = e.tipo_efecto if hasattr(e, "tipo_efecto") else e.get("tipo_efecto")
        bloquea_hacia = e.bloquea_hacia if hasattr(e, "bloquea_hacia") else e.get("bloquea_hacia")
        if tipo == TipoEfecto.MURO and bloquea_hacia == destino_id:
            return True
    return False

def validar_ataque_convencional(
    estado_partida,
    origen_id: str,
    t_origen: TerritorioBase,
    destino_id: str,
    t_destino: TerritorioBase,
    jugador_id: str,
    grafo_aragon
):
    validar_turno(estado_partida.user_turno_actual, jugador_id)
    validar_fase(estado_partida.fase_actual, FasePartida.ATAQUE_CONVENCIONAL)
    
    if _territorio_tiene_inhibidor(t_origen):
        raise ValueError("Tus comunicaciones están inhibidas. No puedes atacar desde este territorio.")
        
    if _ataque_bloqueado_por_muro(t_origen, destino_id):
        raise ValueError("Un Muro Fronterizo bloquea el paso de tus tropas hacia ese territorio.")


    if not grafo_aragon.son_vecinas(origen_id, destino_id):
        raise ValueError("Los territorios no están conectados.")
    
    validar_propiedad_territorio(t_origen, jugador_id, "origen")
    validar_ataque_no_propio(t_origen, t_destino)

    if t_origen.units < 2:
        raise ValueError("Necesitas al menos 2 tropas en el origen para poder atacar.")
    
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
    
def validar_camino_aliado(origen: str, destino: str, owner_id: str, estado_mapa: dict, grafo_aragon):
    """
    Decide qué territorios son del jugador y le pregunta al motor si hay camino.
    """
    # Obtener nodos
    nodos_aliados = obtener_territorios_jugador(estado_mapa, owner_id)

    # Preguntar al grafo            
    if not grafo_aragon.existe_camino_restringido(origen, destino, nodos_aliados):
        raise ValueError("No hay un camino por tus territorios para mover esas tropas.")


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

    if estado_partida.jugadores.get(jugador_id, {}).get("ha_fortificado", False):
        raise ValueError("Ya has realizado tu movimiento de fortificación este turno.")

    validar_camino_aliado(origen_id, destino_id, jugador_id, estado_partida.mapa, grafo_aragon)

    validar_tropas(tropas_a_mover, t_origen.units)
    

    return True

def validar_fase_gestion(estado_partida, jugador_id: str):
    validar_turno(estado_partida.user_turno_actual, jugador_id)
    validar_fase(estado_partida.fase_actual, FasePartida.GESTION)

def validar_asignar_trabajo(estado_partida, jugador_id: str, territorio_id: str, t_destino):
    validar_fase_gestion(estado_partida, jugador_id)
    validar_propiedad_territorio(t_destino, jugador_id, "trabajo")
    
    # Validar que no hay ya un territorio trabajando
    if estado_partida.jugadores[jugador_id].get("territorio_trabajando") is not None:
        raise ValueError("Ya tienes un territorio trabajando en este turno.")
        
    # Validar que este territorio no esté ya investigando (no puede hacer las dos cosas)
    if t_destino.estado_bloqueo is not None:
        raise ValueError("Este territorio ya está ocupado.")

def validar_asignar_investigacion(estado_partida, jugador_id: str, territorio_id: str, t_destino, rama: str):
    validar_fase_gestion(estado_partida, jugador_id)
    validar_propiedad_territorio(t_destino, jugador_id, "investigacion")
    
    # Validar que no hay ya un territorio investigando
    if estado_partida.jugadores[jugador_id].get("territorio_investigando") is not None:
        raise ValueError("Ya tienes un territorio investigando en este turno.")
        
    if t_destino.estado_bloqueo is not None:
        raise ValueError("Este territorio ya está ocupado.")