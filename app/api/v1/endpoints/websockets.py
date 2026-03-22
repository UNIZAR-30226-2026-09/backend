from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
from app.core.event_handler import process_event

# Creamos el router para este endpoint
router = APIRouter()

@router.websocket("/ws/{id_partida}/{username}")

async def websocket_endpoint(websocket: WebSocket, id_partida: str, username: str):

    # Aceptamos la conexión WebSocket
    await manager.connect(websocket, id_partida, username)

    try:

        # Mantenemos la conexión abierta para recibir mensajes
        while True:

            # Esperamos a que el cliente envíe un mensaje en formato JSON
            data = await websocket.receive_json()
            # Enviamos el mensaje para que lo procese
            await process_event(id_partida, username, data)

    except WebSocketDisconnect:

        # Si el cliente se desconecta, lo eliminamos de la partida
        manager.disconnect(id_partida, username)

        # Avisamos al resto de la sala de que este jugador se ha caído
        await manager.broadcast({
            "tipo_evento": "desconexion",
            "jugador": username,
            "mensaje": f"{username} ha abandonado la partida."
        }, id_partida)