from app.core.map_state import game_map_state, map_calculator


def test_son_vecinas_respeta_adyacencias_del_mapa():
    for comarca_id, comarca_info in game_map_state.comarcas.items():
        for vecino in comarca_info.adjacent_to:
            assert map_calculator.son_vecinas(comarca_id, vecino)


def test_son_vecinas_no_marca_vecinos_inexistentes():
    comarcas = list(game_map_state.comarcas.keys())
    origen_id = destino_id = None
    for a in comarcas:
        for b in comarcas:
            if a != b and not map_calculator.son_vecinas(a, b):
                origen_id, destino_id = a, b
                break
        if origen_id:
            break

    assert origen_id is not None, "No se encontró un par de comarcas no colindantes para el test"
    assert map_calculator.son_vecinas(origen_id, destino_id) is False
