
# Contratos de Datos WebSockets (In-Game) - SOBERANÍA

Este documento define la especificación de comunicación en tiempo real durante una partida activa.
Para establecer la conexión, el cliente debe abrir un socket hacia la siguiente URI:
`ws://<host>/api/v1/ws/{id_partida}/{username}`

**Norma general de arquitectura:** Todas las peticiones enviadas desde el Cliente hacia el Servidor deben ser un objeto JSON que incluya obligatoriamente la clave `"accion"`.

---

## 1. SISTEMA DE COMUNICACIÓN (CHAT)

**Dirección:** Cliente -> Servidor
**Descripción:** Emisión de un mensaje de texto a la sala de juego.
**Payload enviado:**
```json
{
  "accion": "CHAT",
  "mensaje": "Alianza confirmada en el sector norte."
}

Dirección: Servidor -> Todos los Clientes (Broadcast)
Descripción: Distribución del mensaje validado a todos los clientes conectados a la partida.
Payload recibido:
{
  "evento": "chat",
  "emisor": "jugador_1",
  "mensaje": "Alianza confirmada en el sector norte."
}

2. GESTIÓN TÁCTICA: MOVIMIENTO DE TROPAS
Dirección: Cliente -> Servidor
Descripción: Solicitud de reubicación de unidades militares entre dos comarcas bajo el control del mismo jugador.
Payload enviado:
{
  "accion": "MOVER_TROPA",
  "origen": "Zaragoza Capital",
  "destino": "Calatayud",
  "cantidad": 5
}

3. RESOLUCIÓN DE CONFLICTOS: ATAQUE
Dirección: Cliente -> Servidor
Descripción: Declaración de una ofensiva militar desde una comarca controlada hacia una comarca enemiga adyacente.
Payload enviado:
{
  "accion": "ATACAR",
  "origen": "Huesca",
  "destino": "Barbastro",
  "tropas": 3
}

4. EVENTOS DE SISTEMA Y CONTROL DE ESTADO
4.1. Excepciones y Errores de Validación
Dirección: Servidor -> Cliente (Unicast)
Descripción: Se transmite exclusivamente al cliente emisor cuando su solicitud no cumple con el esquema establecido (por ejemplo, carece de la clave "accion").
Payload recibido:
{
  "error": "Formato incorrecto. Falta el campo 'accion'."
}

4.2. Notificación de Desconexión
Dirección: Servidor -> Todos los Clientes (Broadcast)
Descripción: Alerta emitida automáticamente por el gestor de conexiones cuando se interrumpe el socket de un participante.
Payload recibido:
{
  "evento": "desconexion",
  "jugador": "jugador_2",
  "mensaje": "jugador_2 ha abandonado la partida."
}