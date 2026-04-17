# Inhibidor de Señal

El Inhibidor de Señal es una habilidad ofensiva de nivel 2 de la rama de Logística. Interrumpe las comunicaciones de un territorio enemigo, inutilizando su capacidad de ataque durante un turno.

## Descripción General
Aplica un efecto temporal sobre un territorio que bloquea al propietario para lanzar tanto ataques convencionales como especiales desde él. Es un control táctico de zona, no hace daño directo.

## Mecánicas de Juego
- **Objetivo:** Un territorio enemigo dentro del rango máximo.
- **Efecto:** Añade `INHIBIDOR_SENAL` a los efectos del territorio.
- **Bloqueo convencional:** `validar_ataque_convencional()` comprueba `_territorio_tiene_inhibidor()` y lanza error si está activo.
- **Bloqueo especial:** El endpoint de `ataque_especial` comprueba igualmente el inhibidor antes de ejecutar el ataque.
- **Duración:** 1 turno. Se decrementa al final de la ronda global (`procesar_todos_los_territorios`).
- **No afecta la defensa:** El territorio puede ser atacado con normalidad.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_inhibidor`): Valida rango, añade el efecto al territorio destino.
2. **Bloqueo convencional:** al realizar un ataque convencional se comprueba si tiene inhibidor y lanza error si está activo. **Los ataques especiales no se ven afectados.** 
3. **Expiración** (`actualizar_estado_efectos_territorio`): Al final de la ronda, `reducir_y_mantener` decrementa la duración. Al llegar a 0 se elimina.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye el territorio afectado:
```json
{
  "resultado": {
    "afectados": [{
      "territorio_id": "Barbastro",
      "efecto_añadido": "inhibidor_senal",
      "duracion": 1
    }]
  }
}
```
Los cambios posteriores en el territorio (expiración del efecto) se comunican mediante `TERRITORIO_ACTUALIZADO`.

## Configuración de Balance
- **Rango:** 2 saltos.
- **Duración:** 1 turno.
- **Precio:** 1000 monedas.
- **Rama / Nivel:** Logística, nivel 2.