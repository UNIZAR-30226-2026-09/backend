# Misil de Crucero

El Misil de Crucero es la tecnología de nivel 2 de la rama de Artillería. Inflige daño porcentual a un territorio dentro de un rango amplio, escalando su efectividad según el tamaño del ejército objetivo.

## Descripción General
Elimina un porcentaje de las tropas presentes en el territorio destino. Cuanto mayor sea el ejército enemigo, más bajas absolutas causa.

## Mecánicas de Juego
- **Objetivo:** Cualquier territorio dentro del rango máximo.
- **Daño:** Porcentaje de las tropas actuales del destino, redondeado hacia arriba (`math.ceil`).
- **Liberación de territorio:** Si el territorio destino llega a 0 tropas, pasa a `neutral`.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_misil_crucero`): Valida rango, aplica daño porcentual con `aplicar_dano_porcentual`, que devuelve las bajas infligidas.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye las bajas infligidas:
```json
{
  "resultado": {
    "afectados": [{
      "territorio_id": "Barbastro",
      "bajas": 4
    }]
  }
}
```

## Configuración de Balance
- **Rango:** Hasta 3 saltos.
- **Daño:** 30% de las tropas del territorio objetivo.
- **Precio:** 1500 monedas.
- **Rama / Nivel:** Artillería, nivel 2.
