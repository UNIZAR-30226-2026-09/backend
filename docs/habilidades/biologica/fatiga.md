# Fatiga

La Fatiga es una capacidad de sabotaje de la categoría de Guerra Biológica. Su objetivo es la parálisis económica y táctica del adversario.

## Descripción General
Esta habilidad aplica un estado de agotamiento al territorio enemigo, impidiendo que las tropas allí destacadas realicen tareas productivas o de investigación.

## Mecánicas de Juego
- **Efecto de Sabotaje:** Bloquea la generación de dinero y la investigación tecnológica en el nodo afectado.
- **Rango:** Puede lanzarse a una distancia considerable de las fronteras propias.
- **Duración:** Persiste durante un número determinado de rondas.
- **Acumulación:** No se puede aplicar fatiga sobre un territorio que ya esté bajo este efecto.

## Integración con WebSockets
La comunicación en tiempo real se gestiona a través de los siguientes eventos:

1. **Lanzamiento (Ataque):** Se emite un evento `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` incluye el territorio saboteado:
   ```json
   {
     "resultado": {
       "afectados": [{
         "territorio_id": "nombre_territorio",
         "efecto_añadido": "fatiga",
         "duracion": 2
       }]
     }
   }
   ```
2. **Evento de Bloqueo:** Si el jugador intenta usar el territorio en la fase de GESTIÓN, el servidor emite un evento `EVENTO_FATIGA` informando de la cancelación de la acción.

## Configuración de Balance
- **Rango:** 3 saltos.
- **Duración:** 2 rondas.
