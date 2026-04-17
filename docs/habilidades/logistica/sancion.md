# Sanciones Internacionales

Las Sanciones Internacionales son la habilidad de mayor nivel de la rama de Logística. Su efecto es devastador a nivel económico: el jugador sancionado no recibe ninguna tropa de refuerzo durante su próximo turno.

## Descripción General
Se lanza contra un **jugador** (se pasa su `usuario_id` como destino). Durante la siguiente fase de Refuerzo de la víctima, sus tropas calculadas se anulan completamente. No tiene efecto sobre el mapa ni sobre tropas ya desplegadas.

## Mecánicas de Juego
- **Objetivo:** Un jugador enemigo (su `usuario_id`).
- **Efecto:** Al inicio del refuerzo de la víctima, si tiene el efecto `SANCIONES` activo, recibe exactamente 0 tropas independientemente de sus territorios, bonos o cualquier otro efecto.
- **Prioridad:** Las sanciones se comprueban antes que cualquier otro modificador (Academia, Propaganda). Si están activas, se sale inmediatamente con 0 tropas — la propaganda enemiga activa no llega a ejecutarse.
- **Aplicación:** El efecto se almacena en `jugadores[victima_id]["efectos"]`.
- **Duración:** 1 turno del jugador víctima.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_sanciones`): Añade el efecto `SANCIONES` al dict del jugador objetivo.
2. **Activación** (`asignar_tropas_reserva`): Al inicio del refuerzo de la víctima, se detecta el efecto, se asignan 0 tropas y se emite `CAMBIO_FASE` inmediatamente.
3. **Expiración** (`actualizar_efectos_jugadores`): Al final de la ronda, `procesar_efectos_genericos` decrementa la duración. Al llegar a 0 se elimina.

## Integración con WebSockets
1. **Lanzamiento:** Se emite `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` incluye el jugador afectado:
   ```json
   {
     "resultado": {
       "afectados": [{
         "jugador_id": "jugador_2",
         "efecto_añadido": "sanciones",
         "duracion": 1
       }]
     }
   }
   ```
2. **Activación en Refuerzo:** Se emite `CAMBIO_FASE` con `tropas_recibidas: 0` y `motivo_refuerzos: "sancion"` para que el front-end muestre el bloqueo:
   ```json
   {
     "tipo_evento": "CAMBIO_FASE",
     "nueva_fase": "REFUERZO",
     "jugador_activo": "jugador_2",
     "tropas_recibidas": 0,
     "motivo_refuerzos": "sancion",
     "fin_fase_utc": "..."
   }
   ```

## Configuración de Balance
- **Duración:** 1 turno del jugador víctima.
- **Precio:** 2500 monedas.
- **Rama / Nivel:** Logística, nivel 3.