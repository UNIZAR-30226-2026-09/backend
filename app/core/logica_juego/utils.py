from fastapi import HTTPException, status
from app.schemas.estado_juego import TerritorioBase, JugadorBase

def obtener_territorios_jugador(mapa: dict, jugador_id: str) -> list[str]:
    """
    Devuelve la lista de IDs de las comarcas que pertenecen a un jugador.
    """
    
    territorios = []
    for t_id, datos in mapa.items():
        propietario = datos.get("owner_id") if isinstance(datos, dict) else datos.owner_id
        if propietario == jugador_id:
            territorios.append(t_id)
    return territorios

def verificar_movimiento_pendiente(jugadores: dict, jugador_id: str):
    datos_jugador_dict = jugadores.get(jugador_id, {})
    jugador_estado = JugadorBase(**datos_jugador_dict)
    
    if jugador_estado.movimiento_conquista_pendiente:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST, 
             detail="Debes mover tropas al territorio conquistado antes de realizar otro ataque."
         )
    return jugador_estado

def obtener_datos_territorio(mapa: dict, territorio_id: str) -> TerritorioBase:
    if territorio_id not in mapa:
        raise HTTPException(status_code=404, detail="Territorio no encontrado en el mapa")
    return TerritorioBase(**mapa[territorio_id])
