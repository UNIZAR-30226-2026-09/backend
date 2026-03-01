# Contratos de Datos REST (Out-Game) - API v1

Este documento define las entradas (Requests) y salidas (Responses) exactas que el Frontend debe enviar y esperar del Backend para los menús y acciones fuera de la partida.

La documentación viva y para hacer pruebas reales está en el Swagger del servidor: `http://localhost:8000/docs`.

---

## 1. USUARIOS Y AUTENTICACIÓN

### Registrar Usuario
- **Endpoint:** `POST /api/v1/usuarios/registro`
- **Request (JSON):**
```json

  {
    "username": "nick_aragon",
    "email": "nick@soberania.es",
    "password": "super_password_123"
  }

Response (200 OK):
{
  "username": "nick_aragon",
  "email": "nick@soberania.es"
}

Login (Obtener Token JWT)
Endpoint: POST /api/v1/usuarios/login

Request (Form-Data): (Ojo Frontend: esto se manda como formulario x-www-form-urlencoded, NO como JSON)

username: "nick_aragon"

password: "super_password_123"

Response (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

Ver mi Perfil
Endpoint: GET /api/v1/usuarios/me

Headers: Authorization: Bearer <tu_token_aqui>

Response (200 OK):
{
  "username": "nick_aragon",
  "email": "nick@soberania.es"
}

2. AMIGOS Y SOCIAL
Enviar Solicitud de Amistad
Endpoint: POST /api/v1/amigos/solicitar

Headers: Authorization: Bearer <tu_token_aqui>

Request (JSON):
{
  "user_2": "ruben"
}

Response (200 OK):
{
  "user_1": "nick_aragon",
  "user_2": "ruben",
  "estado": "pendiente"
}

3. LOBBY Y PARTIDAS
Crear Nueva Partida
Endpoint: POST /api/v1/partidas

Headers: Authorization: Bearer <tu_token_aqui>

Request (JSON):
{
  "config_max_players": 4,
  "config_visibility": "publica",
  "config_timer_seconds": 60
}

Response (200 OK):
{
  "id": 105,
  "config_max_players": 4,
  "config_visibility": "publica",
  "codigo_invitacion": "A8F9B2",
  "config_timer_seconds": 60,
  "estado": "creando",
  "ganador": null
}

4. MAPA DEL MUNDO
Obtener Mapa Inicial
Endpoint: GET /api/v1/mapa

Descripción: El frontend llama aquí una sola vez al cargar la partida para dibujar el tablero de Aragón.

Response (200 OK):
{
  "metadata": {
    "version": "1.0",
    "name": "Aragón",
    "total_comarcas": 33
  },
  "regions": {
    "Zaragoza": {
      "name": "Zaragoza",
      "bonus_troops": 5,
      "comarcas": ["Zaragoza Capital", "Calatayud"]
    }
  },
  "comarcas": {
    "Zaragoza Capital": {
      "name": "Zaragoza Capital",
      "region_id": "Zaragoza",
      "adjacent_to": ["Monegros", "Ribera Baja"]
    }
  }
}
