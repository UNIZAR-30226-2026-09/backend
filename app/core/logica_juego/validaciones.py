# app/core/logica_juego/validaciones.py

def son_adyacentes_mock(grafo_aragon, origen_id: str, destino_id: str) -> bool:
    return True


def validar_tropas_a_mover(tropas_a_mover: int):
    if tropas_a_mover < 1:
        raise ValueError("Debes mover al menos una tropa.")


def validar_ataque_convencional(
    estado_partida,
    origen_id: str,
    datos_origen: dict,
    destino_id: str,
    datos_destino: dict,
    tropas_a_mover: int,
    jugador_id: str,
    grafo_aragon
):
    if estado_partida.user_turno_actual != jugador_id:
        raise ValueError("No es tu turno.")

    if estado_partida.fase_actual != "ataque_convencional":
        raise ValueError("No puedes atacar en esta fase.")

    if not son_adyacentes_mock(grafo_aragon, origen_id, destino_id):
        raise ValueError("Los territorios no están conectados.")

    if str(datos_origen.get("owner_id")) != str(jugador_id):
        raise ValueError("El territorio de origen no te pertenece.")

    if datos_origen.get("owner_id") == datos_destino.get("owner_id"):
        raise ValueError("No puedes atacarte a ti mismo.")

    validar_tropas_a_mover(tropas_a_mover)

    tropas_bloqueadas = datos_origen["units"] if datos_origen.get("status") == "production_mode" else 0
    tropas_libres = datos_origen["units"] - tropas_bloqueadas

    if tropas_a_mover > tropas_libres:
        raise ValueError("No tienes suficientes tropas libres.")

    if tropas_libres - tropas_a_mover < 1:
        raise ValueError("Debes dejar al menos 1 tropa libre en el territorio de origen.")

    return True