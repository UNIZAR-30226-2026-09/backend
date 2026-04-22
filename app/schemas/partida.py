from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

# Nos traemos las opciones fijas (Enums) que hicieron los compis
from app.models.partida import TipoVisibilidad, EstadosPartida, EstadoJugador, FasePartida


class FortificarIn(BaseModel):
    origen: str
    destino: str
    tropas: int = Field(ge=1, description="Cantidad de tropas a desplazar")
 
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

    model_config = ConfigDict(from_attributes=True)

 
# JUGADORES EN LA SALA
 
class JugadorPartidaRead(BaseModel):
    usuario_id: str
    partida_id: int
    turno: int
    estado_jugador: EstadoJugador

    model_config = ConfigDict(from_attributes=True)


 
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

    model_config = ConfigDict(from_attributes=True)


class VotoPausa(BaseModel):
    voto_a_favor: bool


class EmpezarPartidaOut(BaseModel):
    mensaje: str
    partida_id: int
    turno_de: str
    fase: str

class VerEstadoPartidaOut(BaseModel):
    turno_de: str
    fase_actual: str
    fin_fase_utc: datetime
    mapa: Dict[str, Any]
    jugadores: Dict[str, Any]

class PartidaActivaOut(BaseModel):
    partida_id: int
    estado: EstadosPartida
    codigo_invitacion: str
    fase_actual: Optional[FasePartida] = None
    turno_de: Optional[str] = None
    fin_fase_utc: Optional[datetime] = None

class AccionPausaOut(BaseModel):
    mensaje: str
    estado_actual: str

class UnirseOut(BaseModel):
    mensaje: str
    jugadores_en_sala: list[JugadorPartidaRead]
    creador: str

class AbandonarOut(BaseModel):
    mensaje: str

class AsignarTrabajoIn(BaseModel):
    territorio_id: str

class AsignarInvestigacionIn(BaseModel):
    territorio_id: str
    habilidad_id: str

class ComprarTecnologiaIn(BaseModel):
    tecnologia_id: str

class HabilidadOut(BaseModel):
    id: str
    nombre: str
    descripcion: str
    nivel: int
    prerequisito: Optional[Union[str, List[str]]]
    desbloquea: List[str]
    precio: int
    predesbloqueada: bool
    comprada: bool

class TecnologiasPartidaOut(BaseModel):
    ramas: Dict[str, List[HabilidadOut]]