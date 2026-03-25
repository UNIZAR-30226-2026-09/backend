from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
from app.core.event_handler import process_event
from app.core.notifier import notifier

from app.db.session import AsyncSessionLocal
from app.crud.crud_partidas import obtener_estado_partida

router = APIRouter()

@router.websocket("/ws/{id_partida}/{username}")
async def websocket_endpoint(websocket: WebSocket, id_partida: int, username: str):

    # Aceptamos la conexión WebSocket
    await manager.connect(websocket, id_partida, username)
    
    try:
        async with AsyncSessionLocal() as db:
            
            estado = await obtener_estado_partida(db, id_partida)
            
            # Si la partida ya ha empezado, le enviamos el mapa
            if estado:
                await notifier.enviar_sincronizacion_reconexion(id_partida, username, estado)
                
    except Exception as e:
        print(f"[Error WS] Error al sincronizar estado inicial para {username}: {e}")
    try:

        while True:

            # Esperamos a que el cliente envíe un mensaje en formato JSON
            data = await websocket.receive_json()
            # Enviamos el mensaje para que lo procese
            await process_event(id_partida, username, data)

    except WebSocketDisconnect:

        # Si el cliente se desconecta, lo eliminamos de la partida
        manager.disconnect(id_partida, username)

        # Avisamos al resto de la sala de que este jugador se ha caído
        await notifier.notificar_desconexion(id_partida, username)