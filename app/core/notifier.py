from app.core.ws_manager import manager

class GameNotifier:
    """Clase para agrupar todas las notificaciones de la app"""

    @staticmethod
    async def enviar_inicio_partida(
        partida_id: int,
        mapa: dict,
        jugadores: dict,
        turno_de: str,
        fin_fase: object | None = None
    ):
        payload = {
            "tipo_evento": "PARTIDA_INICIADA",
            "mapa": mapa,
            "jugadores": jugadores,
            "turno_de": turno_de,
            "fase_actual": "refuerzo"
        }
        if fin_fase is not None:
            payload["fin_fase_utc"] = fin_fase.isoformat()
        await manager.broadcast(payload, partida_id)

    @staticmethod
    async def notificar_nuevo_jugador(partida_id: int, username: str, color: str):
        await manager.broadcast({
            "tipo_evento": "NUEVO_JUGADOR",
            "jugador": username,
            "color": color
        }, partida_id)


    @staticmethod
    async def enviar_resultado_ataque(partida_id: int, origen_id: str, destino_id: str, resultado):
        await manager.broadcast({
            "tipo_evento": "ATAQUE_RESULTADO",
            "origen": origen_id,
            "destino": destino_id,
            "dados_atacante": resultado.dados_atacante,
            "dados_defensor": resultado.dados_defensor,
            "bajas_atacante": resultado.bajas_atacante,
            "bajas_defensor": resultado.bajas_defensor,
            "victoria": resultado.victoria_atacante
        }, partida_id)

    @staticmethod
    async def enviar_movimiento_conquista(partida_id: int, origen_id: str, destino_id: str, tropas: int, jugador_id: str):
        await manager.broadcast({
            "tipo_evento": "MOVIMIENTO_CONQUISTA",
            "origen": origen_id,
            "destino": destino_id,
            "tropas": tropas,
            "jugador": jugador_id
        }, partida_id)

    @staticmethod
    async def enviar_tropas_colocadas(partida_id: int, jugador_id: str, territorio_id: str, añadidos: int, totales: int):
        await manager.broadcast({
            "tipo_evento": "TROPAS_COLOCADAS",
            "jugador": jugador_id,
            "territorio": territorio_id,
            "tropas_añadidas": añadidos,
            "tropas_totales_ahora": totales
        }, partida_id)


    @staticmethod
    async def enviar_sincronizacion_reconexion(partida_id: int, username: str, estado):
        """Envía el estado completo del mapa solo al usuario que se reconecta (Unicast)."""
        await manager.send_personal_message({
            "tipo_evento": "ACTUALIZACION_MAPA",
            "mapa": estado.mapa,
            "jugadores": estado.jugadores,
            "turno_de": estado.user_turno_actual,
            "fase_actual": estado.fase_actual.value if estado.fase_actual else None,
            "fin_fase_utc": estado.fin_fase_actual.isoformat() if estado.fin_fase_actual else None
        }, partida_id, username)

    @staticmethod
    async def notificar_desconexion(partida_id: int, username: str):
        """Avisa a todos que un jugador se ha ido (Broadcast)."""
        await manager.broadcast({
            "tipo_evento": "DESCONEXION",
            "jugador": username,
            "mensaje": f"{username} ha abandonado la partida."
        }, partida_id)


    @staticmethod
    async def enviar_chat(partida_id: int, emisor: str, mensaje: str):
        """Difunde un mensaje de chat a toda la sala."""
        await manager.broadcast({
            "tipo_evento": "CHAT", 
            "emisor": emisor,
            "mensaje": mensaje
        }, partida_id)

    @staticmethod
    async def enviar_error_formato(partida_id: int, username: str, detalle: str):
        """Avisa a un usuario específico de que su mensaje WS es basura."""
        await manager.send_personal_message({
            "tipo_evento": "ERROR",
            "error": detalle
        }, partida_id, username)


notifier = GameNotifier()
