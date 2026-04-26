# Logs de Partida

Este documento describe el sistema de historial de eventos de una partida. Permite al frontend mostrar un registro de lo ocurrido en turnos anteriores, útil para jugadores que se reconectan o quieren revisar el desarrollo de la partida.

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
  "tipo_evento": "ataque_convencional",
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

### `cambio_turno`
Se genera al inicio de cada turno nuevo.

```json
{
  "turno_de": "pablo"
}
```

---

### `ataque_convencional`
Se genera cada vez que un jugador ejecuta un ataque convencional.

```json
{
  "origen": "zaragoza",
  "destino": "huesca",
  "defensor": "maria",
  "bajas_atacante": 0,
  "bajas_defensor": 1,
  "victoria": true
}
```

---

### `conquista`
Se genera cuando un ataque resulta en victoria y el territorio cambia de dueño. Siempre va acompañado de un `ataque_convencional` en el mismo turno.

```json
{
  "territorio_conquistado": "huesca",
  "anterior_dueno": "maria"
}
```

---

### `ataque_especial`
Se genera cuando un jugador lanza una tecnología o arma especial.

```json
{
  "tipo_ataque": "MISIL_CRUCERO",
  "origen": "zaragoza",
  "destino": "lerida"
}
```

Los valores posibles de `tipo_ataque` están documentados en [`habilidades/`](habilidades/).

---

### `jugador_eliminado`
Se genera cuando un jugador pierde su último territorio.

```json
{
  "eliminado": "maria"
}
```

---

### `fin_partida`
Se genera cuando la partida termina. El campo `user` contiene al ganador.

```json
{
  "ganador": "pablo"
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
    "tipo_evento": "ataque_convencional",
    "user": "pablo",
    "datos": {
      "origen": "zaragoza",
      "destino": "huesca",
      "defensor": "maria",
      "bajas_atacante": 0,
      "bajas_defensor": 1,
      "victoria": true
    }
  },
  {
    "id": 16,
    "partida_id": 7,
    "turno_numero": 4,
    "fase": "refuerzo",
    "timestamp": "2026-04-26T12:38:00Z",
    "tipo_evento": "cambio_turno",
    "user": "pablo",
    "datos": {
      "turno_de": "pablo"
    }
  }
]
```
