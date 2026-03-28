


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