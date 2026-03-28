import json
import networkx as nx
from pathlib import Path
from app.schemas.map import MapDataSchema

# Calculamos la ruta absoluta al archivo JSON
DATA_PATH = Path(__file__).parent / "data" / "map_aragon.json"

def load_map_data() -> MapDataSchema:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return MapDataSchema(**data)
    except Exception as e:
        print(f"Error crítico cargando el mapa: {e}")
        raise e

# Caché del mapa original (Pydantic)
game_map_state: MapDataSchema = load_map_data()


# ----------------------------------------------------------------------------
# CALCULADORA DE GRAFOS (T7)
# ----------------------------------------------------------------------------
class MapGraph:
    def __init__(self, map_data: MapDataSchema):
        self.graph = nx.Graph()
        self._build_graph(map_data)

    def _build_graph(self, map_data: MapDataSchema):
        """Convierte el JSON en un grafo matemático de nodos y aristas."""
        for comarca_id, comarca_info in map_data.comarcas.items():
            self.graph.add_node(comarca_id)
            for vecino in comarca_info.adjacent_to:
                self.graph.add_edge(comarca_id, vecino)

    def son_vecinas(self, origen: str, destino: str) -> bool:
        """Devuelve True si dos comarcas están tocándose (ataque convencional)."""
        return self.graph.has_edge(origen, destino)

    def obtener_vecinos(self, comarca_id: str) -> list[str]:
        """Devuelve la lista de vecinos directos de una comarca."""
        if self.graph.has_node(comarca_id):
            return list(self.graph.neighbors(comarca_id))
        return []

    def calcular_distancia(self, origen: str, destino: str) -> int:
        """Calcula los saltos entre dos comarcas (útil para guerra tecnológica/misiles)."""
        try:
            return nx.shortest_path_length(self.graph, source=origen, target=destino)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return -1

    def existe_camino_restringido(self, origen: str, destino: str, nodos_permitidos: list[str]) -> bool:
        """
        Comprueba si hay ruta entre origen y destino pasando SOLO por los nodos indicados.
        """
        if origen not in nodos_permitidos or destino not in nodos_permitidos:
            return False
            
        subgrafo = self.graph.subgraph(nodos_permitidos)
        
        try:
            return nx.has_path(subgrafo, source=origen, target=destino)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return False

# Instancia global lista para ser importada desde cualquier sitio del backend
map_calculator = MapGraph(game_map_state)