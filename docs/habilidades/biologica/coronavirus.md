# Coronavirus

El Coronavirus es la capacidad táctica de máximo nivel en la categoría de Guerra Biológica. Su principal ventaja es su alta infectividad y capacidad de expansión autónoma.

## Descripción General
Esta habilidad infecta un territorio objetivo, causando un impacto inicial de bajas y estableciendo un foco de contagio persistente que puede propagarse a nodos adyacentes de forma aleatoria.

## Mecánicas de Juego
- **Impacto Inicial:** Aplica un daño porcentual inmediato al lanzarse (parámetro dano_inicial).
- **Daño Recurrente:** Resta un porcentaje de tropas (parámetro dano_recurrente) al inicio del turno del afectado.
- **Expansión:** Al finalizar la ronda, existe una probabilidad (parámetro probabilidad_expansion) de contagiar a vecinos.
- **Duración Dinámica:** Se calcula como la duración base multiplicada por el número de jugadores.

## Integración con WebSockets
La comunicación en tiempo real se gestiona a través de los siguientes eventos:

1. **Lanzamiento (Ataque):** Se emite un evento `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` incluye las bajas iniciales y el estado de la infección:
   ```json
   {
     "resultado": {
       "afectados": [{
         "territorio_id": "nombre_territorio",
         "bajas_iniciales": 15,
         "efecto_añadido": "coronavirus",
         "duracion": 4
       }]
     }
   }
   ```
2. **Daño Recurrente y Expansión:** Se comunican mediante eventos `TERRITORIO_ACTUALIZADO`.

## Configuración de Balance
- **Impacto Inicial:** 40% de tropas.
- **Daño Recurrente:** 10% de tropas.
- **Probabilidad de Expansión:** 25% por vecino.
- **Duración:** 2 rondas por jugador.
