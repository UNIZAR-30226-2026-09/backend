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
        "nueva_fase": "REFUERZO",
        "jugador_activo": "jugador_1",
        "fin_fase_utc": "2026-03-22T15:30:00Z",
        "tropas_recibidas": 5,
        "motivo_refuerzos": "ACADEMIA_MILITAR" 
    }
    ```
* **Nota:** `motivo_refuerzos` puede ser "NORMAL", "ACADEMIA_MILITAR" o "SANCION_INTERNACIONAL" (0 tropas).*

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
---

## 4. SISTEMA DE PRESENCIA Y AMIGOS (Canal Global)

Para recibir notificaciones sociales fuera de una partida, el cliente debe abrir un socket hacia la siguiente URI:
`ws://<host>/api/v1/global/{username}`

### 4.1. Notificación de Presencia (Online/Offline)
* **Dirección:** Servidor -> Cliente (Personalizado)
* **Descripción:** Se emite automáticamente cuando un usuario de tu lista de amigos (aceptados) se conecta o desconecta de la aplicación.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "PRESENCIA",
        "username": "nombre_del_amigo",
        "estado": "online" // "offline"
    }
    ```

### 4.2. Notificación de Solicitud de Amistad
* **Dirección:** Servidor -> Cliente (Personalizado)
* **Descripción:** Se emite al instante cuando otro jugador te envía una solicitud de amistad HTTP y te encuentras con la aplicación abierta.
* **Payload recibido:**
    ```json
    {
        "tipo_evento": "NUEVA_SOLICITUD_AMISTAD",
        "de": "nombre_del_solicitante"
    }
 
## 5. GUERRA TECNOLÓGICA (ATAQUES ESPECIALES)

### 5.1. Notificación de Ataque Especial
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite inmediatamente cuando un jugador lanza un poder (misiles, virus, etc.).
    ```json
    {
        "tipo_evento": "ATAQUE_ESPECIAL",
        "atacante": "jugador_1",
        "tipo_ataque": "MISIL_NUCLEAR",
        "origen": "Huesca",
        "destino": "Barbastro"
    }
    ```

### 5.2. Actualización de Territorio (Efectos Persistentes)
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Evento crítico enviado cuando un territorio cambia debido a efectos que perduran (ej. bajas automáticas por Gripe Aviar o expansión de patógenos).
    ```json
    {
        "tipo_evento": "TERRITORIO_ACTUALIZADO",
        "nombre_territorio": "Barbastro",
        "territorio": {
            "owner_id": "jugador_2",
            "units": 8,
            "estado_bloqueo": "CONGELADO",
            "efectos": [
                {
                    "tipo_efecto": "GRIPE_AVIAR",
                    "duracion_restante": 2,
                    "origen_jugador_id": "jugador_1"
                }
            ]
        }
    }
    ```

---

## 6. GESTIÓN ECONÓMICA E INVESTIGACIÓN

### 6.1. Investigación Completada
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
    ```json
    {
        "tipo_evento": "INVESTIGACION_COMPLETADA",
        "jugador": "jugador_1",
        "territorio": "Huesca",
        "nuevas_tecnologias": ["coronavirus", "fatiga"]
    }
    ```

### 6.2. Trabajo Completado (Economía)
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
    ```json
    {
        "tipo_evento": "TRABAJO_COMPLETADO",
        "jugador": "jugador_1",
        "monedas_ganadas": 15,
        "total_monedas": 45
    }
    ```

### 6.3. Evento de Fatiga
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Notifica que una acción de producción o investigación ha sido bloqueada este turno por un efecto de fatiga enemigo.
    ```json
    {
        "tipo_evento": "EVENTO_FATIGA",
        "jugador": "jugador_1",
        "territorio": "Teruel",
        "mensaje": "La producción se ha detenido por fatiga laboral enemiga."
    }
    ```

### 6.4. Propaganda Activada
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se dispara al intentar colocar tropas en un territorio infectado por propaganda enemiga, informando del robo de unidades.
    ```json
    {
        "tipo_evento": "PROPAGANDA_ACTIVADA",
        "victima": "jugador_1",
        "beneficiario": "jugador_2",
        "tropas_robadas": 2
    }
    ```

## 7. FINALIZACIÓN Y ELIMINACIÓN
### 7.1. Jugador Eliminado
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Se emite cuando un jugador pierde todos sus territorios y es expulsado de la partida.
    ```json
    {
        "tipo_evento": "JUGADOR_ELIMINADO",
        "jugador": "jugador_3"
    }
    ```

### 7.2. Partida Finalizada
* **Dirección:** Servidor -> Todos los Clientes (Broadcast)
* **Descripción:** Evento de cierre que identifica al ganador absoluto de la partida.
    ```json
    {
        "tipo_evento": "PARTIDA_FINALIZADA",
        "ganador": "jugador_1"
    }
    ```

## 7. EVENTOS PENDIENTES DE DOCUMENTAR
Hay eventos pendientes de documentar en limpio!