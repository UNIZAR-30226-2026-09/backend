from app.core.notifier import notifier
from app.core.logica_juego.constantes import MENSAJES_CHAT_PERMITIDOS, REACCIONES_CHAT_PERMITIDAS
from app.crud import crud_logs
from app.db.session import AsyncSessionLocal

async def process_event(id_partida: int, username: str, data: dict):
    
    # Comprobamos que el JSON tiene la clave "accion"
    accion = data.get("accion")

    if not accion:
        # Si envían basura, le mandamos un error solo a ese jugador
        await notifier.enviar_error_formato(
            id_partida, 
            username, 
            "Formato incorrecto. Falta el campo 'accion'."
        )
        return

    if accion == "CHAT":
        await handle_chat(id_partida, username, data)
        
    else:
        print(f"[Aviso] Acción desconocida recibida de {username}: {accion}")


async def handle_chat(id_partida: int, username: str, data: dict):
    tipo_chat = data.get("tipo_chat")
    contenido = data.get("contenido")
    
    if tipo_chat == "mensaje" and contenido not in MENSAJES_CHAT_PERMITIDOS:
        print(f"[Aviso] {username} intentó enviar un mensaje no permitido: {contenido}")
        return
    elif tipo_chat == "reaccion" and contenido not in REACCIONES_CHAT_PERMITIDAS:
        print(f"[Aviso] {username} intentó enviar una reacción no permitida: {contenido}")
        return
    elif tipo_chat not in ["mensaje", "reaccion"]:
        print(f"[Aviso] Formato de chat inválido de {username}")
        return

    print(f"[CHAT LOG] {username} en Partida {id_partida} envió {tipo_chat}: {contenido}")

    async with AsyncSessionLocal() as db:
        nuevo_log = await crud_logs.crear_log(
            db=db,
            partida_id=id_partida,
            turno_numero=0, 
            fase="chat",
            tipo_evento=f"chat_{tipo_chat}",
            user=username,
            datos={"texto": contenido}
        )
        timestamp_str = str(nuevo_log.timestamp)

    await notifier.enviar_chat(id_partida, username, tipo_chat, contenido, timestamp_str)