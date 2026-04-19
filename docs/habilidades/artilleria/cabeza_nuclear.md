# Cabeza Nuclear

La Cabeza Nuclear es una de las tecnologías de nivel 3 de la rama de Artillería. Es el arma de destrucción masiva individual más potente: inflige un daño fijo devastador sobre un único territorio.

## Descripción General
Elimina un número fijo de tropas del territorio destino, independientemente del tamaño del ejército. Predecible y letal contra cualquier guarnición.

## Mecánicas de Juego
- **Objetivo:** Cualquier territorio dentro del rango máximo.
- **Daño:** Número fijo de bajas configurado en `dano_fijo`.
- **Liberación de territorio:** Si el territorio destino llega a 0 tropas, pasa a `neutral`.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_cabeza_nuclear`): Valida rango, aplica daño fijo con `aplicar_dano_fijo`.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye las bajas infligidas:
```json
{
  "resultado": {
    "afectados": [{
      "territorio_id": "Barbastro",
      "bajas": 15
    }]
  }
}
```

## Configuración de Balance
- **Rango:** Hasta 3 saltos.
- **Daño:** Fijo (ver `dano_fijo` en `config_ataques_especiales.py`).
- **Precio:** 3000 monedas.
- **Rama / Nivel:** Artillería, nivel 3.
