# Muro Fronterizo

El Muro Fronterizo es una habilidad defensiva de nivel 3 de la rama de Logística. Sella una frontera entre dos territorios adyacentes, impidiendo que ninguno ataque al otro a través de ese borde durante un turno.

## Descripción General
Se aplica sobre la frontera entre el territorio de origen y un territorio adyacente. El efecto se registra en **ambos** territorios, bloqueando la frontera en las dos direcciones.

## Mecánicas de Juego
- **Objetivo:** Un territorio adyacente (exactamente 1 salto, sin excepciones).
- **Efecto:** Añade el efecto `MURO` con un campo `bloquea_hacia` a ambos territorios de la frontera.
- **Bloqueo bidireccional:** Ninguno de los dos territorios puede atacar al otro mientras el muro esté activo, incluyendo el propio jugador que lo construyó.
- **No afecta la fortificación:** El movimiento de tropas propio durante la fase de Fortificación no está restringido por el muro.
- **Duración:** 1 turno. Se decrementa al final de la ronda global.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_muro`): Valida que los territorios sean adyacentes, añade `MURO` con `bloquea_hacia` al dict de efectos de ambos territorios.
2. **Bloqueo activo**: `validar_ataque_convencional()` llama a `_ataque_bloqueado_por_muro()`, que comprueba si el territorio de origen tiene un efecto `MURO` apuntando al destino del ataque.
3. **Expiración** (`actualizar_estado_efectos_territorio`): Al final de la ronda, `reducir_y_mantener` decrementa la duración. Al llegar a 0 se elimina de ambos territorios de forma independiente.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye los dos territorios sellados:
```json
{
  "resultado": {
    "afectados": [
      {"territorio_id": "Huesca", "bloquea_hacia": "Barbastro", "efecto_añadido": "muro", "duracion": 1},
      {"territorio_id": "Barbastro", "bloquea_hacia": "Huesca", "efecto_añadido": "muro", "duracion": 1}
    ]
  }
}
```
La expiración del efecto se comunica mediante `TERRITORIO_ACTUALIZADO` en ambos territorios.

## Configuración de Balance
- **Rango:** Exactamente 1 salto (territorios adyacentes).
- **Duración:** 1 turno.
- **Precio:** 1500 monedas.
- **Rama / Nivel:** Logística, nivel 3.