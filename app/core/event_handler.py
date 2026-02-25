from app.core.ws_manager import manager

from app.core.ws_manager import manager

async def process_event(id_partida: int, username: str, data: dict):
    
    # 1. Comprobamos que el JSON tiene la clave "accion"
    accion = data.get("accion")

    if not accion:
        # Si envían basura, le mandamos un error solo a ese jugador
        await manager.send_personal_message(
            {"error": "Formato incorrecto. Falta el campo 'accion'."}, 
            id_partida, 
            username
        )
        return

    # 2. ENRUTADOR (Switch/Case de acciones)
    if accion == "CHAT":
        await handle_chat(id_partida, username, data)
        
    elif accion == "MOVER_TROPA":
        await handle_mover_tropa(id_partida, username, data)
        
    elif accion == "ATACAR":
        await handle_atacar(id_partida, username, data)
        
    else:
        print(f"[Aviso] Acción desconocida recibida de {username}: {accion}")


# =============================================================================
# FUNCIONES BASE (La "tubería" vacía para que tus compañeros programen luego)
# =============================================================================

async def handle_chat(id_partida: int, username: str, data: dict):

    print(f"[CHAT] {username} dice: {data.get('mensaje')}")
    # El chat es lo único que sí podemos dejar funcionando como "eco"
    await manager.broadcast({
        "evento": "chat",
        "emisor": username,
        "mensaje": data.get("mensaje", "")
    }, id_partida)

async def handle_mover_tropa(id_partida: int, username: str, data: dict):

    print(f"[MOVER] {username} quiere mover. Datos: {data}")
    # TODO: Aquí otro compañero programará la lógica de movimiento en el mapa

async def handle_atacar(id_partida: int, username: str, data: dict):
    
    print(f"[ATACAR] {username} lanza un ataque. Datos: {data}")
    # TODO: Aquí otro compañero programará la validación de la batalla