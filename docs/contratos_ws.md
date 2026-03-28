# Contratos de Datos WebSockets

Este documento define la especificación de comunicación en tiempo real durante una partida activa.
Para establecer la conexión, el cliente debe abrir un socket hacia la siguiente URI:
`ws://<host>/api/v1/ws/{id_partida}/{username}`

**Norma general de arquitectura:** Todas las respuestas enviadas desde el Servidor hacia los Clientes serán objetos JSON que incluirán obligatoriamente la clave `"tipo_evento"`. El Frontend deberá usar esta clave para derivar el mensaje a la función de UI correspondiente.

---

## 1. SISTEMA DE COMUNICACIÓN (CHAT)

* **Dirección:** Cliente -> Servidor
* **Payload enviado:**
    ```json
    {
      "accion": "CHAT",
      "mensaje": "Alianza confirmada en el sector norte."
    }
    ```

* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Payload recibido:**
    ```json
    {
      "tipo_evento": "CHAT",
      "emisor": "jugador_1",
      "mensaje": "Alianza confirmada en el sector norte."
    }
    ```

## 2. EVENTOS TÁCTICOS (Respuestas a peticiones HTTP)

### 2.1. Resultado de un Ataque
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando un jugador resuelve un combate convencional.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "ATAQUE_RESULTADO",
        "origen": "Huesca",
        "destino": "Barbastro",
        "bajas_atacante": 0,
        "bajas_defensor": 2,
        "victoria": true,
        "tropas_restantes_origen": 4,
        "tropas_restantes_defensor": 0
    }
    ```

### 2.2. Movimiento de Tropas (Conquista o Fortificación)
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando un jugador traslada tropas al territorio recién conquistado o cuando mueve tropas durante la fase de Fortificación.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "MOVIMIENTO_CONQUISTA",
        "origen": "Huesca",
        "destino": "Barbastro",
        "tropas": 3,
        "jugador": "jugador_1"
    }
    ```

### 2.3. Colocación de Tropas (Fase de Refuerzo)
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando un jugador despliega nuevos recursos en sus territorios.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "TROPAS_COLOCADAS",
        "jugador": "jugador_1",
        "territorio": "Zaragoza Capital",
        "tropas_añadidas": 5,
        "tropas_totales_ahora": 12
    }
    ```

## 3. EVENTOS DE SISTEMA Y CONTROL DE ESTADO

### 3.1. Cambio de Fase o Turno
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando expira el temporizador o el jugador pasa de fase manualmente. Controla el flujo de la Máquina de Estados.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "CAMBIO_FASE",
        "nueva_fase": "ATAQUE",
        "jugador_activo": "jugador_1",
        "fin_fase_utc": "2026-03-22T15:30:00Z"
    }
    ```
### 3.2. Inicio de Partida
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite a todos los jugadores en el lobby cuando el host inicia la partida mediante el endpoint HTTP `/empezar`. Indica al Frontend que debe cambiar de la pantalla de espera al tablero.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "PARTIDA_INICIADA",
        "mapa": { "Huesca": { "owner_id": "jugador_1", "units": 0 }, ... },
        "jugadores": {
            "jugador_1": { "numero_jugador": 1 },
            "jugador_2": { "numero_jugador": 2 }
        },
        "turno_de": "jugador_1",
        "fase_actual": "refuerzo",
        "fin_fase_utc": "2026-03-22T15:30:00Z"
    }
    ```

### 3.3. Sincronización de Reconexión
* **Dirección:** Servidor -> Cliente (Unicast)
* **Descripción:** Se transmite exclusivamente al cliente que acaba de abrir el WebSocket **si la partida ya había empezado**. Permite al Frontend en una reconexión.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "ACTUALIZACION_MAPA",
        "mapa": { "Huesca": { "owner_id": "jugador_1", "units": 5 }, ... },
        "jugadores": { "jugador_1": { "tropas_reserva": 0 }, ... },
        "turno_de": "jugador_2",
        "fase_actual": "ataque",
        "fin_fase_utc": "2026-03-22T15:35:00Z"
    }
    ```

### 3.4. Notificación de Desconexión
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Alerta emitida automáticamente por el gestor de conexiones cuando se interrumpe el socket de un participante.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "DESCONEXION",
        "jugador": "jugador_2",
        "mensaje": "jugador_2 ha abandonado la partida."
    }
    ```

### 3.5. Notificación de Nuevo Jugador
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando un nuevo usuario se une a la sala (vía HTTP). Permite a los que ya están en el lobby actualizar su lista de amigos.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "NUEVO_JUGADOR",
        "jugador": "nombre"
    }
    ```

### 3.6. Excepciones y Errores (WS Directo)
* **Dirección:** Servidor -> Cliente (Unicast)
* **Descripción:** Se transmite exclusivamente al cliente emisor si envía un mensaje WS malformado.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "ERROR",
        "error": "Formato incorrecto. Falta el campo 'accion'."
    }
    ```

## 4. EVENTOS PENDIENTES DE DOCUMENTAR
Hay eventos pendientes de documentar en limpio!