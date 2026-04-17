# Mortero Táctico

El Mortero Táctico es la tecnología de nivel 1 de la rama de Artillería. Es el arma más sencilla y barata, con un daño aleatorio y rango corto pero preciso.

## Descripción General
Inflige un número aleatorio de bajas fijas sobre un territorio a exactamente 2 saltos de distancia. No puede lanzarse contra territorios adyacentes ni a mayor distancia — el rango es exacto.

## Mecánicas de Juego
- **Objetivo:** Un territorio a exactamente 2 saltos del origen.
- **Daño:** Número aleatorio de bajas fijas dentro de un rango configurado (`dano_min` – `dano_max`).
- **Rango exacto:** La validación usa `rango_exacto=True`. Ni más cerca ni más lejos.
- **Liberación de territorio:** Si el territorio destino llega a 0 tropas, pasa a `neutral`.

## Flujo de Ejecución
1. **Lanzamiento** (`ejecutar_mortero_tactico`): Valida rango exacto, calcula bajas aleatorias con `random.randint`, aplica con `aplicar_dano_fijo`.

## Integración con WebSockets
Se emite `ATAQUE_ESPECIAL` al lanzarlo. El campo `resultado` incluye las bajas infligidas:
```json
{
  "resultado": {
    "afectados": [{
      "territorio_id": "Barbastro",
      "bajas": 3
    }]
  }
}
```

## Configuración de Balance
- **Rango:** Exactamente 2 saltos.
- **Daño:** Entre 1 y 4 bajas (aleatorio).
- **Precio:** 500 monedas.
- **Rama / Nivel:** Artillería, nivel 1.
