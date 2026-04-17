# Academia Militar

La Academia Militar es la tecnología de nivel 1 de la rama de Logística. Es una mejora pasiva permanente: no se activa manualmente, sino que funciona de forma automática cada vez que el jugador recibe refuerzos.

## Descripción General
Una vez comprada e incorporada a `tecnologias_compradas`, multiplica todas las tropas de refuerzo del jugador al inicio de cada turno. No tiene duración ni puede expirar.

## Mecánicas de Juego
- **Tipo:** Pasiva permanente. No se lanza ni consume usos.
- **Efecto:** Multiplica las tropas de refuerzo calculadas (territorios ÷ 3, mínimo 3) por el multiplicador configurado, redondeando hacia arriba.
- **Orden de aplicación:** Se aplica antes que el robo de Propaganda. Si el jugador también tiene Propaganda enemiga activa, el multiplicador se aplica primero y luego se roba el porcentaje sobre el total ya multiplicado.
- **Compatibilidad:** No es compatible con Sanciones Internacionales. Si el jugador tiene sanciones ese turno, recibe 0 tropas y la Academia no aplica.

## Flujo de Ejecución
1. **Desbloqueo:** Se predestroquea al completar una investigación de logística nivel 1 (`INVESTIGACION_COMPLETADA`).
2. **Compra:** El jugador la adquiere en la tienda (`tecnologias_compradas`).
3. **Activación automática:** Cada vez que comienza la fase de Refuerzo del jugador, `asignar_tropas_reserva()` detecta `academia_militar` en `tecnologias_compradas` y llama a `calcular_refuerzos_academia()`.

## Integración con WebSockets
No genera ningún evento propio al activarse. El efecto se comunica dentro del evento `CAMBIO_FASE` mediante el campo `motivo_refuerzos`:

```json
{
  "tipo_evento": "CAMBIO_FASE",
  "nueva_fase": "REFUERZO",
  "jugador_activo": "jugador_1",
  "tropas_recibidas": 8,
  "motivo_refuerzos": "academia",
  "fin_fase_utc": "2026-04-17T15:30:00Z"
}
```

El valor `"academia"` en `motivo_refuerzos` indica al frontend que las tropas ya incluyen el bono multiplicador.

## Configuración de Balance
- **Multiplicador:** ×1.5 (resultado redondeado hacia arriba con `math.ceil`).
- **Precio:** 500 monedas.
- **Rama / Nivel:** Logística, nivel 1.