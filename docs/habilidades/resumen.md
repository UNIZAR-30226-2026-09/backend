# Resumen de Habilidades Especiales — Guía para Frontend

Este documento describe **cuándo ocurre cada cosa** durante el flujo de un turno, qué eventos WebSocket esperar en cada momento y qué habilidades especiales pueden estar activas. Para los detalles técnicos de cada habilidad, consultar los docs individuales en las subcarpetas.

---

## Flujo de un Turno Completo

```
REFUERZO → GESTIÓN → ATAQUE CONVENCIONAL → ATAQUE ESPECIAL → FORTIFICACIÓN → (siguiente jugador) → REFUERZO ...
```

---

## 1. Transición al REFUERZO (cambio de jugador)

Este es el momento más cargado de efectos. Ocurre cuando el jugador anterior completa su fase de Fortificación.

### 1.1 Fin de ronda — efectos globales
Se procesan **antes** de cambiar el jugador activo. Afectan a todos los territorios del mapa.

| Qué ocurre | WS recibido |
|---|---|
| El Coronavirus intenta expandirse a territorios vecinos (probabilidad 25% por vecino) | `TERRITORIO_ACTUALIZADO` por cada nuevo contagio |
| Todas las duraciones de efectos de territorio se decrementan (Gripe Aviar, Coronavirus, Inhibidor, Muro, Fatiga) | `TERRITORIO_ACTUALIZADO` si el efecto expira o cambia |
| Todas las duraciones de efectos de jugador se decrementan (Propaganda, Sanciones) | — (silencioso) |

### 1.2 Daño de enfermedades — inicio del turno del nuevo jugador
Se aplica **sobre los territorios del jugador que va a recibir el turno**, antes de que reciba sus tropas.

| Efecto activo | Qué ocurre | WS recibido |
|---|---|---|
| **Gripe Aviar** | Resta 1 tropa fija por territorio infectado | `TERRITORIO_ACTUALIZADO` por cada territorio afectado |
| **Coronavirus** | Resta 10% de tropas por territorio infectado | `TERRITORIO_ACTUALIZADO` por cada territorio afectado |

### 1.3 Asignación de tropas de refuerzo
Se calculan las tropas para el nuevo jugador activo. Se aplican modificadores en este orden:

| Condición | Efecto | `motivo_refuerzos` | WS recibido |
|---|---|---|---|
| Tiene **Sanciones Internacionales** | Recibe 0 tropas. Se detiene aquí, no se evalúan más modificadores. | `"sancion"` | `CAMBIO_FASE` |
| Tiene **Academia Militar** | Tropas × 1.5 (redondeado arriba) | `"academia"` | `CAMBIO_FASE` |
| Tiene **Propaganda** de un enemigo | Se le roba un 50% de tropas calculadas; el atacante las recibe | `"propaganda"` | `PROPAGANDA_ACTIVADA` + `CAMBIO_FASE` |
| Sin modificadores | Tropas normales (territorios ÷ 3, mínimo 3) | `"normal"` | `CAMBIO_FASE` |

> **Nota:** Academia y Propaganda pueden coexistir. El orden es: calcular base → aplicar academia → aplicar robo de propaganda.

**Evento `CAMBIO_FASE` al inicio de REFUERZO:**
```json
{
  "tipo_evento": "CAMBIO_FASE",
  "nueva_fase": "REFUERZO",
  "jugador_activo": "jugador_2",
  "tropas_recibidas": 5,
  "motivo_refuerzos": "normal",
  "fin_fase_utc": "2026-04-17T15:30:00Z"
}
```

---

## 2. Fase REFUERZO

El jugador activo coloca tropas de su reserva en sus territorios.

| Qué ocurre | WS recibido |
|---|---|
| Jugador coloca tropas en un territorio | `TROPAS_COLOCADAS` |

No hay habilidades especiales que se activen automáticamente en esta fase.

---

## 3. Fase GESTIÓN

El jugador resuelve trabajo e investigación iniciados en el turno anterior.

| Condición | Qué ocurre | WS recibido |
|---|---|---|
| Territorio trabajando, sin **Fatiga** | Se generan monedas (tropas × 100). Territorio liberado. | `TRABAJO_COMPLETADO` + `TERRITORIO_ACTUALIZADO` |
| Territorio trabajando, **con Fatiga** | No se generan monedas. Sigue bloqueado otro turno. | `EVENTO_FATIGA` |
| Territorio investigando, sin **Fatiga** | Se sube el nivel de rama y se predesbloquean tecnologías. | `INVESTIGACION_COMPLETADA` + `TERRITORIO_ACTUALIZADO` |
| Territorio investigando, **con Fatiga** | No avanza la investigación. Sigue bloqueado otro turno. | `EVENTO_FATIGA` |

---

## 4. Fase ATAQUE CONVENCIONAL

El jugador puede atacar territorios enemigos adyacentes.

| Condición | Qué ocurre | WS recibido |
|---|---|---|
| Territorio origen tiene **Inhibidor de Señal** | El ataque es rechazado | Error HTTP 400 (no WS) |
| Frontera tiene **Muro Fronterizo** | El ataque es rechazado | Error HTTP 400 (no WS) |
| Ataque resuelto | Bajas calculadas por dados, posible conquista | `ATAQUE_RESULTADO` |
| Victoria con conquista | El jugador debe mover tropas al nuevo territorio | `ATAQUE_RESULTADO` (victoria: true) |
| Jugador mueve tropas a territorio conquistado | — | `MOVIMIENTO_CONQUISTA` |
| Jugador sin territorios tras la conquista | Jugador eliminado | `JUGADOR_ELIMINADO` |
| Solo queda un jugador | Fin de partida | `PARTIDA_FINALIZADA` |

---

## 5. Fase ATAQUE ESPECIAL

El jugador puede lanzar habilidades de guerra tecnológica y biológica que haya comprado.

> El **Inhibidor de Señal** **no** bloquea los ataques especiales, solo los convencionales.

Todas las habilidades emiten `ATAQUE_ESPECIAL` al lanzarse. El campo `resultado.afectados` varía por tipo:

### Habilidades de Artillería (daño inmediato a territorio)

| Habilidad | Objetivo | Daño | Campo `resultado` |
|---|---|---|---|
| **Mortero Táctico** | Territorio a exactamente 2 saltos | 1–4 bajas fijas (aleatorio) | `territorio_id`, `bajas` |
| **Misil de Crucero** | Territorio a ≤3 saltos | 30% de tropas | `territorio_id`, `bajas` |
| **Cabeza Nuclear** | Territorio a ≤3 saltos | Daño fijo elevado | `territorio_id`, `bajas` |
| **Bomba de Racimo** | Territorio a ≤3 saltos | Fijo en objetivo + 20% en cada vecino | `territorio_id`, `bajas` × N territorios |

### Habilidades Biológicas (efectos persistentes en territorio)

| Habilidad | Objetivo | Efecto | Campo `resultado` |
|---|---|---|---|
| **Gripe Aviar** | Territorio enemigo | Añade efecto `gripe_aviar` (3 turnos) | `territorio_id`, `efecto_añadido`, `duracion` |
| **Coronavirus** | Territorio a ≤1 salto | Daño inmediato 40% + efecto expansivo | `territorio_id`, `bajas`, `efecto_añadido`, `duracion` |
| **Fatiga** | Territorio a ≤3 saltos | Bloquea trabajo e investigación (2 turnos) | `territorio_id`, `efecto_añadido`, `duracion` |
| **Vacuna Universal** | Territorio propio | Cura todos los territorios propios conectados | `territorio_id` × N territorios curados |

### Habilidades de Operaciones y Logística (efectos en jugador o frontera)

| Habilidad | Objetivo | Efecto | Campo `resultado` |
|---|---|---|---|
| **Inhibidor de Señal** | Territorio enemigo a ≤2 saltos | Bloquea ataques convencionales desde ese territorio (1 turno) | `territorio_id`, `efecto_añadido`, `duracion` |
| **Muro Fronterizo** | Territorio adyacente | Sella la frontera en ambas direcciones (1 turno) | 2 entradas: `territorio_id` + `bloquea_hacia` |
| **Propaganda Subversiva** | Jugador enemigo | Roba 50% de sus tropas de refuerzo en su próximo turno | `jugador_id`, `efecto_añadido`, `duracion` |
| **Sanciones Internacionales** | Jugador enemigo | Su próximo refuerzo es 0 tropas | `jugador_id`, `efecto_añadido`, `duracion` |

---

## 6. Fase FORTIFICACIÓN

El jugador puede mover tropas entre sus propios territorios conectados.

| Qué ocurre | WS recibido |
|---|---|
| Jugador mueve tropas por su red | `MOVIMIENTO_CONQUISTA` |

El **Muro Fronterizo** **no** bloquea la fortificación, solo los ataques.

---

## Referencia Rápida: Efectos y Cuándo Actúan

| Efecto | Se aplica en | Afecta a | Expira en |
|---|---|---|---|
| `gripe_aviar` | Inicio REFUERZO del propietario | Territorio (−1 tropa/turno) | Fin de ronda (−1 duración) |
| `coronavirus` | Inicio REFUERZO del propietario | Territorio (−10%/turno) + expansión | Fin de ronda (−1 duración) |
| `fatiga` | Fase GESTIÓN | Territorio (bloquea trabajo/investigación) | Fin de ronda (−1 duración) |
| `inhibidor_senal` | Fase ATAQUE CONVENCIONAL | Territorio (bloquea ataque convencional) | Fin de ronda (−1 duración) |
| `muro` | Fase ATAQUE CONVENCIONAL | Frontera entre 2 territorios (bidireccional) | Fin de ronda (−1 duración) |
| `propaganda` | Inicio REFUERZO de la víctima | Jugador (−50% tropas robadas) | Fin de ronda (−1 duración) |
| `sanciones` | Inicio REFUERZO de la víctima | Jugador (0 tropas ese turno) | Fin de ronda (−1 duración) |
