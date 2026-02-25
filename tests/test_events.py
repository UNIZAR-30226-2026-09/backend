import asyncio
from app.core.ws_manager import manager
from app.core.event_handler import process_event

# Reutilizamos nuestro WebSocket de mentira
class MockWebSocket:
    def __init__(self, owner_name):
        self.owner_name = owner_name

    async def accept(self):
        pass

    async def send_json(self, data):
        print(f"📥 [{self.owner_name} recibe por WS]: {data}")


async def probar_enrutador():
    print("=== INICIANDO PRUEBA DEL CARTERO DE EVENTOS ===\n")
    
    # 1. Metemos a Pepe y a Juan en la partida 1
    ws_pepe = MockWebSocket("Pepe")
    ws_juan = MockWebSocket("Juan")
    
    await manager.connect(ws_pepe, id_partida=1, username="Pepe")
    await manager.connect(ws_juan, id_partida=1, username="Juan")
    
    print("\n--- PRUEBA 1: JSON sin campo 'accion' (Debería dar error a Pepe) ---")
    await process_event(id_partida=1, username="Pepe", data={"mensaje": "Hola pero sin accion"})
    
    print("\n--- PRUEBA 2: Acción CHAT (Debería llegar a Pepe y Juan) ---")
    await process_event(id_partida=1, username="Pepe", data={"accion": "CHAT", "mensaje": "¡Os voy a conquistar Zaragoza!"})

    print("\n--- PRUEBA 3: Acción ATACAR (Debería imprimir el log de la función vacía) ---")
    await process_event(id_partida=1, username="Juan", data={"accion": "ATACAR", "origen": "Huesca", "destino": "Zaragoza"})
    
    print("\n--- PRUEBA 4: Acción INVENTADA ---")
    await process_event(id_partida=1, username="Pepe", data={"accion": "HACER_TRAMPAS"})

if __name__ == "__main__":
    asyncio.run(probar_enrutador())