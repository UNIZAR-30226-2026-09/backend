from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Nos traemos las opciones fijas (Enums) que hicieron los compis
from app.models.partida import TipoVisibilidad, EstadosPartida, EstadoJugador, FasePartida, ColorJugador

 
# PARTIDA PRINCIPAL (La sala de espera y configuración)
 
class PartidaCreate(BaseModel):
    # Lo que nos manda el creador de la sala desde el móvil
    config_max_players: int = Field(default=4, ge=2, le=4) # Entre 2 y 4 jugadores
    config_visibility: TipoVisibilidad = TipoVisibilidad.PUBLICA
    config_timer_seconds: int = Field(default=60, gt=0) # El turno no puede durar 0 segundos

class PartidaRead(BaseModel):
    # Lo que ve la gente en el lobby
    id: int
    config_max_players: int
    config_visibility: TipoVisibilidad
    codigo_invitacion: str
    config_timer_seconds: int
    estado: EstadosPartida
    ganador: Optional[str] = None

    class Config:
        from_attributes = True

 
# JUGADORES EN LA SALA
 
class JugadorPartidaRead(BaseModel):
    usuario_id: str
    partida_id: int
    turno: int
    estado_jugador: EstadoJugador
    color: ColorJugador

    class Config:
        from_attributes = True

 
# ESTADO DEL TABLERO (El núcleo del juego)
 
class EstadoPartidaUpdate(BaseModel):
    # Cuando un jugador mueve tropas o ataca, validamos la entrada de esos JSON
    mapa: Dict[str, Any]
    jugadores: Dict[str, Any]

class EstadoPartidaRead(BaseModel):
    partida_id: int
    fase_actual: FasePartida
    fin_fase_actual: datetime
    user_turno_actual: str
    mapa: dict
    jugadores: dict

    class Config:
        from_attributes = True