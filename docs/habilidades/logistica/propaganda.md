# Propaganda Subversiva

La Propaganda Subversiva es una habilidad de la categoría de Operaciones y Logística. A diferencia de los ataques directos, su efecto es económico: intercepta los refuerzos del enemigo antes de que lleguen al campo de batalla.

## Descripción General
Se lanza sobre un **jugador** (no sobre un territorio). Durante la siguiente fase de Refuerzo de la víctima, un porcentaje de las tropas que iba a recibir es interceptado y redirigido al atacante.

## Mecánicas de Juego
- **Objetivo:** Un jugador enemigo (se pasa su `usuario_id` como destino).
- **Efecto:** Al inicio del turno de refuerzo de la víctima, se calcula su reserva normal y se le resta un porcentaje. Esas tropas se añaden directamente a la reserva del atacante.
- **Aplicación:** El efecto se almacena en `jugadores[victima_id]["efectos"]`, no en el mapa.
- **Exclusividad:** Un jugador no puede tener más de una propaganda activa simultáneamente.
- **Duración:** 2 turnos del jugador víctima. El efecto se decrementa al final de cada ronda global (`procesar_efectos_fin_de_turno`).
- **Compatibilidad:** Se aplica después del bono de Academia Militar. Si la víctima recibe sanciones ese turno (0 tropas), la propaganda no roba nada.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_propaganda`): Se añade el efecto al dict del jugador víctima.
2. **Activación** (`asignar_tropas_reserva`): Al inicio del refuerzo de la víctima, `calcular_robo_propaganda()` detecta el efecto, calcula las tropas robadas y las transfiere al beneficiario.
3. **Expiración** (`actualizar_efectos_jugadores`): Se decrementa `duracion` al final de la ronda. Cuando llega a 0, el efecto se elimina.

## Integración con WebSockets
1. **Lanzamiento:** Se emite `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` incluye el jugador afectado:
   ```json
   {
     "resultado": {
       "afectados": [{
         "jugador_id": "jugador_2",
         "efecto_añadido": "propaganda",
         "duracion": 2
       }]
     }
   }
   ```
2. **Activación en Refuerzo:** Se emite `PROPAGANDA_ACTIVADA` (Broadcast) cuando efectivamente se roba:
   ```json
   {
     "tipo_evento": "PROPAGANDA_ACTIVADA",
     "victima": "jugador_2",
     "beneficiario": "jugador_1",
     "tropas_robadas": 3
   }
   ```
3. **Cambio de Fase:** Se emite `CAMBIO_FASE` con `motivo_refuerzos: "propaganda"` para que el front-end sepa que las tropas recibidas son reducidas.

## Configuración de Balance
- **Porcentaje de robo:** 50% de los refuerzos calculados (redondeado hacia abajo).
- **Duración:** 2 turnos del jugador víctima.