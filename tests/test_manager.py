import asyncio
from app.core.ws_manager import ConnectionManager

# 1. Creamos un "Falso" WebSocket para que el manager no se queje
class MockWebSocket:
    def __init__(self, owner_name):
        self.owner_name = owner_name

    async def accept(self):
        print(f"🔌 [Sistema] Conexión HTTP aceptada para {self.owner_name}")

    async def send_json(self, data):
        # En lugar de enviarlo por internet, simplemente lo imprimimos en la consola
        print(f"📥 [{self.owner_name} recibe]: {data}")

# 2. Nuestra función de prueba
async def probar_logica():
    print("=== INICIANDO PRUEBA DEL MANAGER ===\n")
    manager = ConnectionManager()
    
    # Creamos dos usuarios falsos
    ws_pepe = MockWebSocket("Pepe")
    ws_juan = MockWebSocket("Juan")

    # Los conectamos a la partida 12
    await manager.connect(ws_pepe, id_partida=12, username="Pepe")
    await manager.connect(ws_juan, id_partida=12, username="Juan")

    print(f"\nEstado interno (Diccionario): {manager.active_connections}")

    print("\n=== PROBANDO EL BROADCAST (Mensaje a toda la partida) ===")
    await manager.broadcast({"evento": "chat", "texto": "¡Hola Aragón!"}, id_partida=12)

    print("\n=== PROBANDO DESCONEXIÓN ===")
    manager.disconnect(id_partida=12, username="Pepe")
    print(f"Usuarios restantes en la partida 12: {list(manager.active_connections[12].keys())}")

# 3. Ejecutamos la prueba asíncrona
if __name__ == "__main__":
    asyncio.run(probar_logica())