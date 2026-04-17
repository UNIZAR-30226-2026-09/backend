from fastapi import WebSocket
from typing import Dict, Optional
import json

class ConnectionManager:

    def __init__(self):

        # Diccionario para separar a los jugadores por partidas
        # Formato: { id_partida: { username: WebSocket_Object } }
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        self.global_connections: Dict[str, WebSocket] = {}


    @staticmethod
    def _normalizar_id_partida(id_partida, contexto: str) -> Optional[int]:
        """Convierte id_partida a int y registra errores de formato."""
        try:
            return int(id_partida)
        except (TypeError, ValueError):
            print(f"[WS] id_partida inválido al {contexto}: {id_partida}")
            return None

    async def connect(self, websocket: WebSocket, id_partida: int, username: str):

        id_partida_normalizado = self._normalizar_id_partida(id_partida, "conectar")
        if id_partida_normalizado is None:
            await websocket.close(code=1008)
            return
        id_partida = id_partida_normalizado

        # Aceptar la conexión WebSocket y agregar el jugador a la partida correspondiente7
        await websocket.accept()

        # Si la partida no existe, la creamos 
        if id_partida not in self.active_connections:
            self.active_connections[id_partida] = {}

        # Agregar el jugador a la partida
        self.active_connections[id_partida][username] = websocket
        print(f"Jugador {username} conectado a la partida {id_partida}")

    def disconnect(self, id_partida: int, username: str):

        id_partida_normalizado = self._normalizar_id_partida(id_partida, "desconectar")
        if id_partida_normalizado is None:
            return
        id_partida = id_partida_normalizado

        # Elimina al jugador de la partida correspondiente
        if id_partida in self.active_connections:
            if username in self.active_connections[id_partida]:
                del self.active_connections[id_partida][username]
                print(f"Jugador {username} desconectado de la partida {id_partida}")

        # Si la partida no tiene jugadores, la eliminamos del diccionario
        if not self.active_connections[id_partida]:
            del self.active_connections[id_partida]

    async def send_personal_message(self, message: str, id_partida: int, username: str):

        id_partida_normalizado = self._normalizar_id_partida(id_partida, "enviar mensaje personal")
        if id_partida_normalizado is None:
            return
        id_partida = id_partida_normalizado

        # Enviar un mensaje a un jugador específico en una partida
        if id_partida in self.active_connections:
            if username in self.active_connections[id_partida]:
                websocket = self.active_connections[id_partida][username]
                await websocket.send_json(message)

    async def broadcast(self, message: dict, id_partida: int):

        id_partida_normalizado = self._normalizar_id_partida(id_partida, "hacer broadcast")
        if id_partida_normalizado is None:
            return
        id_partida = id_partida_normalizado

        # Enviar un mensaje a todos los jugadores de una partida
        if id_partida in self.active_connections:
            for websocket in self.active_connections[id_partida].values():
                await websocket.send_json(message)

    async def connect_global(self, websocket: WebSocket, username: str):
        """Conecta al usuario al canal global de presencia."""
        await websocket.accept()
        self.global_connections[username] = websocket

    def disconnect_global(self, username: str):
        """Desconecta al usuario del canal global."""
        if username in self.global_connections:
            del self.global_connections[username]

manager = ConnectionManager()