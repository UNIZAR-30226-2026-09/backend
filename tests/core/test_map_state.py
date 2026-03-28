import networkx as nx
from app.core.map_state import game_map_state, map_calculator, MapGraph


def _grafo_simple():
    """
    Grafo de prueba: A — B — C — D
                             |
                             E
    """
    mg = object.__new__(MapGraph)
    mg.graph = nx.Graph()
    mg.graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("C", "E")])
    return mg


# ---------------------------------------------------------------------------
# existe_camino_restringido
# ---------------------------------------------------------------------------

def test_existe_camino_restringido_vecinos_directos():
    grafo = _grafo_simple()
    assert grafo.existe_camino_restringido("A", "B", ["A", "B", "C", "D", "E"]) is True


def test_existe_camino_restringido_camino_indirecto():
    grafo = _grafo_simple()
    # A y D no son vecinos directos, pero hay camino A-B-C-D
    assert grafo.existe_camino_restringido("A", "D", ["A", "B", "C", "D"]) is True


def test_existe_camino_restringido_bloqueado_por_enemigo():
    grafo = _grafo_simple()
    # C es enemigo: A y D quedan desconectados
    assert grafo.existe_camino_restringido("A", "D", ["A", "B", "D"]) is False


def test_existe_camino_restringido_origen_no_permitido():
    grafo = _grafo_simple()
    assert grafo.existe_camino_restringido("A", "C", ["B", "C", "D"]) is False


def test_existe_camino_restringido_destino_no_permitido():
    grafo = _grafo_simple()
    assert grafo.existe_camino_restringido("A", "D", ["A", "B", "C"]) is False


def test_existe_camino_restringido_mismo_nodo():
    grafo = _grafo_simple()
    assert grafo.existe_camino_restringido("B", "B", ["B"]) is True


def test_existe_camino_restringido_nodos_vacios():
    grafo = _grafo_simple()
    assert grafo.existe_camino_restringido("A", "B", []) is False


# ---------------------------------------------------------------------------
# Tests existentes
# ---------------------------------------------------------------------------

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
