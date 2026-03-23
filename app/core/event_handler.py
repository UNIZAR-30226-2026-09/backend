from app.core.notifier import notifier

async def process_event(id_partida: int, username: str, data: dict):
    
    # 1. Comprobamos que el JSON tiene la clave "accion"
    accion = data.get("accion")

    if not accion:
        # Si envían basura, le mandamos un error solo a ese jugador
        await notifier.enviar_error_formato(
            id_partida, 
            username, 
            "Formato incorrecto. Falta el campo 'accion'."
        )
        return

    # 2. ENRUTADOR (Switch/Case de acciones)
    if accion == "CHAT":
        await handle_chat(id_partida, username, data)
        
    else:
        print(f"[Aviso] Acción desconocida recibida de {username}: {accion}")


async def handle_chat(id_partida: int, username: str, data: dict):
    mensaje = data.get("mensaje", "")
    print(f"[CHAT LOG] {username} en Partida {id_partida}: {mensaje}")

    await notifier.enviar_chat(id_partida, username, mensaje)