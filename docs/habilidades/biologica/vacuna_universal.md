# Vacuna Universal

La Vacuna Universal es una capacidad de apoyo de la categoría de Guerra Biológica. Su función es la eliminación masiva de patógenos y estados alterados biológicos en territorios controlados por el jugador.

## Descripción General
Esta habilidad sana un territorio infectado y se propaga automáticamente por toda la red de territorios propios conectados. Es la defensa fundamental contra epidemias masivas.

## Mecánicas de Juego
- **Objetivo:** Debe lanzarse sobre un territorio propio.
- **Efecto de Curación:** Elimina instantáneamente cualquier efecto de Gripe Aviar, Coronavirus o Fatiga.
- **Propagación:** Utiliza un algoritmo de búsqueda en anchura (BFS) para viajar desde el territorio destino a todos los territorios adyacentes del mismo propietario.

## Integración con WebSockets
La comunicación en tiempo real se gestiona a través de los siguientes eventos:

1. **Lanzamiento (Ataque):** Se emite un evento `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` contiene la lista completa de territorios limpiados:
   ```json
   {
     "resultado": {
       "afectados": [
         { "territorio_id": "territorio_1" },
         { "territorio_id": "territorio_2" }
       ]
     }
   }
   ```
2. **Actualización de Estado:** El servidor emite una `ACTUALIZACION_MAPA` completa para asegurar que todos los clientes reflejan la limpieza de iconos de virus en toda la red curada.

## Configuración de Balance
- **Enfermedades Curables:** Gripe Aviar, Coronavirus, Fatiga.
- **Rango:** 1 (Lanzamiento sobre territorio propio).
