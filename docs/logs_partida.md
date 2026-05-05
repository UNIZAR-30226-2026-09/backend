# Logs de Partida

Este documento describe el sistema de historial de eventos de una partida. Permite al frontend mostrar un registro de lo ocurrido en turnos anteriores, útil para jugadores que se reconectan o quieren revisar el desarrollo de la partida.

> **Nota para el frontend:** la mayoría de `tipo_evento` coinciden exactamente con los eventos WebSocket, por lo que se puede reutilizar la misma función `renderEvento()` para ambas fuentes. Los eventos exclusivos del log (sin WS equivalente) están marcados con 🗂️.

---

## Endpoint

```
GET /api/v1/partidas/{partida_id}/logs?limit=50
```

- **Autenticación:** JWT requerido (header `Authorization: Bearer <token>`)
- **Parámetros de query:**
  - `limit` (opcional, por defecto `50`): número máximo de eventos a devolver
- **Orden:** más reciente primero

---

## Estructura de cada log

```json
{
  "id": 42,
  "partida_id": 7,
  "turno_numero": 3,
  "fase": "ataque_convencional",
  "timestamp": "2026-04-26T12:34:56Z",
  "tipo_evento": "ATAQUE_RESULTADO",
  "user": "pablo",
  "datos": { ... }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | int | Identificador único del log |
| `partida_id` | int | Partida a la que pertenece |
| `turno_numero` | int | Número de turno global en el que ocurrió |
| `fase` | string | Fase activa cuando ocurrió el evento |
| `timestamp` | datetime (UTC) | Momento exacto del evento |
| `tipo_evento` | string | Tipo de evento (ver tabla de tipos) |
| `user` | string \| null | Usuario que realizó la acción |
| `datos` | object | Información específica del evento (ver abajo) |

---

## Tipos de evento y su `datos`

### `PARTIDA_INICIADA`
Se genera cuando el host arranca la partida.

```json
{
  "jugadores": ["pablo", "maria", "juan"],
  "primer_turno": "pablo"
}
```

---

### `CAMBIO_FASE`
Se genera en dos situaciones distintas con `datos` diferentes:

**Al cambiar de turno** (automático o por timer):
```json
{
  "turno_de": "pablo",
  "tropas_recibidas": 5,
  "motivo_refuerzos": "normal"
}
```
Valores posibles de `motivo_refuerzos`: `normal`, `academia`, `propaganda`, `sancion`.

**Al pasar fase manualmente** (el jugador pulsa "pasar fase"):
```json
{
  "fase_anterior": "refuerzo",
  "fase_nueva": "ataque_convencional"
}
```

---

### `ATAQUE_RESULTADO`
Se genera cada vez que un jugador ejecuta un ataque convencional.

```json
{
  "origen": "zaragoza",
  "destino": "huesca",
  "defensor": "maria",
  "bajas_atacante": 0,
  "bajas_defensor": 1,
  "victoria": true,
  "tropas_restantes_origen": 3,
  "tropas_restantes_defensor": 0
}
```

---

### `conquista` 🗂️
Se genera cuando un ataque resulta en victoria y el territorio cambia de dueño. Siempre acompañado de un `ATAQUE_RESULTADO` en el mismo turno.

```json
{
  "territorio_conquistado": "huesca",
  "anterior_dueno": "maria"
}
```

---

### `MOVIMIENTO_CONQUISTA`
Se genera en dos situaciones (mismo mensaje en ambas):
- Cuando el jugador mueve tropas al territorio recién conquistado.
- Cuando el jugador fortifica (mueve tropas entre territorios propios en fase de fortificación).

```json
{
  "origen": "zaragoza",
  "destino": "huesca",
  "tropas": 2
}
```

---

### `ataque_especial`
Se genera cuando un jugador lanza una tecnología o arma especial.

```json
{
  "tipo_ataque": "MISIL_CRUCERO",
  "origen": "zaragoza",
  "destino": "lerida",
  "resultado": { ... }
}
```

Los valores posibles de `tipo_ataque` y la estructura de `resultado` están documentados en [`habilidades/`](habilidades/).

---

### `TROPAS_COLOCADAS`
Se genera cuando un jugador coloca tropas de su reserva en un territorio.

```json
{
  "territorio": "zaragoza",
  "cantidad": 3
}
```

---

### `trabajar` 🗂️
Se genera cuando un jugador asigna un territorio a producir monedas.

```json
{
  "territorio": "zaragoza"
}
```

---

### `investigar` 🗂️
Se genera cuando un jugador asigna un territorio a investigar una habilidad.

```json
{
  "territorio": "zaragoza",
  "habilidad": "MISIL_CRUCERO"
}
```

---

### `comprar_tecnologia` 🗂️
Se genera cuando un jugador compra una tecnología con sus monedas.

```json
{
  "tecnologia": "MISIL_CRUCERO",
  "precio": 3
}
```

---

### `JUGADOR_ELIMINADO`
Se genera cuando un jugador pierde su último territorio.

```json
{
  "eliminado": "maria",
  "por_quien": "pablo"
}
```

`por_quien` puede ser `null` si la eliminación fue causada por un efecto (enfermedad, etc.) y no por un ataque directo.

---

### `PARTIDA_FINALIZADA`
Se genera cuando la partida termina.

```json
{
  "ganador": "pablo"
}
```

---

### `abandonar_partida` 🗂️
Se genera cuando un jugador no-host abandona la sala durante el lobby.

```json
{
  "usuario": "maria"
}
```

---

## Ejemplo de respuesta completa

```json
[
  {
    "id": 18,
    "partida_id": 7,
    "turno_numero": 4,
    "fase": "ataque_convencional",
    "timestamp": "2026-04-26T12:40:01Z",
    "tipo_evento": "conquista",
    "user": "pablo",
    "datos": {
      "territorio_conquistado": "huesca",
      "anterior_dueno": "maria"
    }
  },
  {
    "id": 17,
    "partida_id": 7,
    "turno_numero": 4,
    "fase": "ataque_convencional",
    "timestamp": "2026-04-26T12:39:58Z",
    "tipo_evento": "ATAQUE_RESULTADO",
    "user": "pablo",
    "datos": {
      "origen": "zaragoza",
      "destino": "huesca",
      "defensor": "maria",
      "bajas_atacante": 0,
      "bajas_defensor": 1,
      "victoria": true,
      "tropas_restantes_origen": 3,
      "tropas_restantes_defensor": 0
    }
  },
  {
    "id": 16,
    "partida_id": 7,
    "turno_numero": 4,
    "fase": "refuerzo",
    "timestamp": "2026-04-26T12:38:00Z",
    "tipo_evento": "CAMBIO_FASE",
    "user": "pablo",
    "datos": {
      "turno_de": "pablo",
      "tropas_recibidas": 5,
      "motivo_refuerzos": "normal"
    }
  }
]
```
