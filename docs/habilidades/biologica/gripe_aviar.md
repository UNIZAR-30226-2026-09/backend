# Gripe Aviar

La Gripe Aviar es una capacidad táctica perteneciente a la categoría de Guerra Biológica. Su propósito es el desgaste continuado de las guarniciones enemigas mediante una infección persistente.

## Descripción General
Esta habilidad infecta un territorio objetivo, provocando la pérdida gradual de tropas. El impacto se manifiesta de forma recurrente mientras el efecto permanezca activo, mermando las fuerzas del oponente cada vez que este inicia su fase de refuerzo.

## Mecánicas de Juego
- **Tipo de Daño:** Resta un número fijo de unidades (parámetro dano_por_turno).
- **Momento de Aplicación:** El daño se procesa al inicio de la fase de REFUERZO del jugador propietario del territorio infectado.
- **Duración:** El efecto persiste durante un número determinado de rondas.
- **Neutralización de Territorio:** Si el número de unidades llega a cero por la enfermedad, el territorio pasa a ser neutral.
- **Curación:** Puede ser eliminada mediante una Vacuna Universal.

## Integración con WebSockets
La comunicación en tiempo real se gestiona a través de dos eventos:

1. **Lanzamiento (Ataque):** Se emite un evento `ATAQUE_ESPECIAL` (Broadcast). El campo `resultado` contiene la información del estado alterado:
   ```json
   {
     "resultado": {
       "afectados": [{
         "territorio_id": "nombre_territorio",
         "efecto_añadido": "gripe_aviar",
         "duracion": 3
       }]
     }
   }
   ```
2. **Aplicación del Daño:** Cada vez que se procesa el daño al inicio del turno del afectado, el servidor emite un evento `TERRITORIO_ACTUALIZADO` con el nuevo recuento de tropas y la duración restante del efecto.

## Configuración de Balance
- **Daño por turno:** 1 unidad.
- **Duración:** 3 rondas.
