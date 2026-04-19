# Bomba de Racimo

La Bomba de Racimo es una de las tecnologías de nivel 3 de la rama de Artillería. A diferencia de la Cabeza Nuclear, su poder reside en el daño en área: además de golpear el objetivo principal, inflige daño porcentual a todos los territorios adyacentes.

## Descripción General
Aplica daño fijo al territorio objetivo y daño porcentual a cada uno de sus vecinos en el mapa, sin distinción de propietario. Puede afectar tanto a territorios enemigos como a los propios.

## Mecánicas de Juego
- **Objetivo principal:** Recibe un número fijo de bajas (`dano_fijo_objetivo`).
- **Daño colateral:** Cada territorio adyacente al objetivo recibe un porcentaje de sus propias tropas como bajas (`dano_colindantes`). Cuanto mayor sea el ejército vecino, más daño absoluto recibe.
- **Sin distinción de bando:** El daño colateral afecta a cualquier territorio vecino, incluidos los propios.
- **Liberación de territorio:** Cualquier territorio (principal o colateral) que llegue a 0 tropas pasa a `neutral`.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_bomba_racimo`): Valida rango, aplica `aplicar_dano_fijo` al objetivo, luego itera sobre todos los vecinos con `map_calculator.obtener_vecinos` y aplica `aplicar_dano_porcentual` a cada uno.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye el objetivo y todos los colaterales con sus bajas:
```json
{
  "resultado": {
    "afectados": [
      {"territorio_id": "Barbastro", "bajas": 10},
      {"territorio_id": "Huesca",    "bajas": 2},
      {"territorio_id": "Monzon",    "bajas": 1}
    ]
  }
}
```
El primer elemento siempre es el objetivo principal; los siguientes son los colaterales.

## Configuración de Balance
- **Rango:** Hasta 3 saltos.
- **Daño objetivo:** Fijo (ver `dano_fijo_objetivo` en `config_ataques_especiales.py`).
- **Daño colateral:** Porcentual por vecino (ver `dano_colindantes`).
- **Precio:** 2000 monedas.
- **Rama / Nivel:** Artillería, nivel 3.
