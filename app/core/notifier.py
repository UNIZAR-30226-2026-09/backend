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
    async def enviar_fin_partida(partida_id: int, ganador: str):

        await manager.broadcast({
            "tipo_evento": "PARTIDA_FINALIZADA",
            "ganador": ganador,
            "mensaje": f"La partida ha terminado. {ganador} ha conquistado todos los territorios."
        }, partida_id)

    @staticmethod
    async def notificar_sala_cerrada(partida_id: int):
        await manager.broadcast({
            "tipo_evento": "SALA_CERRADA",
            "mensaje": "El host ha abandonado la sala. La partida ha sido cancelada."
        }, partida_id)

    @staticmethod
    async def notificar_nuevo_jugador(partida_id: int, username: str):
        await manager.broadcast({
            "tipo_evento": "NUEVO_JUGADOR",
            "jugador": username,
        }, partida_id)


    @staticmethod
    async def enviar_resultado_ataque(partida_id: int, origen_id: str, destino_id: str, resultado):
        await manager.broadcast({
            "tipo_evento": "ATAQUE_RESULTADO",
            "origen": origen_id,
            "destino": destino_id,
            "bajas_atacante": resultado.bajas_atacante,
            "bajas_defensor": resultado.bajas_defensor,
            "victoria": resultado.victoria_atacante,
            "tropas_restantes_origen": resultado.tropas_restantes_origen,
            "tropas_restantes_defensor": resultado.tropas_restantes_defensor,
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
    async def enviar_ataque_especial(partida_id: int, atacante_id: str, tipo_ataque: str, origen_id: str, destino_id: str, resultado=None):
        payload = {
            "tipo_evento": "ataque_especial",
            "atacante": atacante_id,
            "tipo": tipo_ataque,
            "origen": origen_id,
            "destino": destino_id
        }
        if resultado is not None:
            payload["resultado"] = resultado

        await manager.broadcast(payload, partida_id)

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
    async def enviar_cambio_fase(partida_id: int, nueva_fase: str, jugador_activo: str, tropas_recibidas: int, motivo_refuerzos: str, fin_fase_utc: str):
        await manager.broadcast({
            "tipo_evento": "CAMBIO_FASE",
            "nueva_fase": nueva_fase,
            "jugador_activo": jugador_activo,
            "tropas_recibidas": tropas_recibidas,
            "motivo_refuerzos": motivo_refuerzos,
            "fin_fase_utc": fin_fase_utc
        }, partida_id)

    @staticmethod
    async def enviar_jugador_eliminado(partida_id: int, username: str):

        await manager.broadcast({
            "tipo_evento": "JUGADOR_ELIMINADO",
            "username": username,
            "mensaje": f"¡{username} ha sido borrado del mapa!"
        }, partida_id)

    @staticmethod
    async def enviar_actualizacion_territorio(partida_id: int, territorio_id: str, data_territorio: dict):
        """
        Envía el objeto completo del territorio: tropas, propietario y estados (virus, bloqueos, etc.)
        """

        await manager.broadcast({
            "tipo_evento": "TERRITORIO_ACTUALIZADO",
            "territorio_id": territorio_id,
            "detalles": data_territorio
        }, partida_id)

    @staticmethod
    async def enviar_investigacion_completada(partida_id: int, usuario_id: str, rama: str, nivel: int, territorio_id: str, habilidades_desbloqueadas: list, habilidades_siguientes: list):
        """
        Notifica que una investigación ha tenido éxito y se han desbloqueado tecnologías.
        """
        await manager.broadcast({
            "tipo_evento": "INVESTIGACION_COMPLETADA",
            "usuario_id": usuario_id,
            "rama": rama,
            "nivel": nivel,
            "territorio_id": territorio_id,
            "habilidades_desbloqueadas": habilidades_desbloqueadas,
            "habilidades_siguientes": habilidades_siguientes,
            "mensaje": f"Investigación completada en {territorio_id}. Habilidad: {habilidades_desbloqueadas}."
        }, partida_id)

    @staticmethod
    async def enviar_trabajo_completado(partida_id: int, usuario_id: str, territorio_id: str, ganancia: int):
        """
        Notifica que un territorio ha terminado de producir monedas.
        """
        await manager.broadcast({
            "tipo_evento": "TRABAJO_COMPLETADO",
            "usuario_id": usuario_id,
            "territorio_id": territorio_id,
            "ganancia": ganancia,
            "mensaje": f"Producción en {territorio_id} finalizada. ¡+ {ganancia} monedas!"
        }, partida_id)

    @staticmethod
    async def enviar_evento_fatiga(partida_id: int, usuario_id: str, territorio_id: str, accion: str):
        """
        Notifica que una acción (investigar/trabajar) no ha avanzado este turno por fatiga.
        """
        await manager.broadcast({
            "tipo_evento": "EVENTO_FATIGA",
            "usuario_id": usuario_id,
            "territorio_id": territorio_id,
            "accion_bloqueada": accion,
            "mensaje": f"Las tropas en {territorio_id} están demasiado cansadas para terminar de {accion}."
        }, partida_id)


    @staticmethod
    async def enviar_propaganda_activada(partida_id: int, victima_id: str, beneficiario_id: str, cantidad: int):

        await manager.broadcast({
            "tipo_evento": "PROPAGANDA_ACTIVADA",
            "victima_id": victima_id,
            "beneficiario": beneficiario_id,
            "cantidad_robada": cantidad,
            "mensaje": f"¡Propaganda! {beneficiario_id} ha interceptado {cantidad} tropas de {victima_id}."
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


    @staticmethod
    async def enviar_solicitud_pausa(partida_id: int, solicitante: str):
        await manager.broadcast({
            "tipo_evento": "SOLICITUD_PAUSA",
            "solicitante": solicitante,
            "mensaje": f"{solicitante} ha solicitado pausar la partida. Todos deben votar."
        }, partida_id)

    @staticmethod
    async def enviar_voto_registrado(partida_id: int, votante: str, a_favor: bool, votos_a_favor: int, total: int):
        await manager.broadcast({
            "tipo_evento": "VOTO_PAUSA",
            "votante": votante,
            "a_favor": a_favor,
            "votos_a_favor": votos_a_favor,
            "total_jugadores": total,
        }, partida_id)

    @staticmethod
    async def enviar_pausa_rechazada(partida_id: int, votante: str):
        await manager.broadcast({
            "tipo_evento": "PAUSA_RECHAZADA",
            "votante": votante,
            "mensaje": f"{votante} ha votado en contra. La pausa ha sido cancelada."
        }, partida_id)

    @staticmethod
    async def enviar_partida_pausada(partida_id: int):
        await manager.broadcast({
            "tipo_evento": "PARTIDA_PAUSADA",
            "mensaje": "La partida ha sido pausada por unanimidad."
        }, partida_id)

    @staticmethod
    async def enviar_partida_reanudada(partida_id: int, nueva_fase: str, jugador_activo: str, fin_fase_utc: str):
        await manager.broadcast({
            "tipo_evento": "PARTIDA_REANUDADA",
            "nueva_fase": nueva_fase,
            "jugador_activo": jugador_activo,
            "fin_fase_utc": fin_fase_utc,
            "mensaje": "La partida ha sido reanudada."
        }, partida_id)


notifier = GameNotifier()
