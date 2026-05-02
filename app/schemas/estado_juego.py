from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class EfectoActivo(BaseModel):
    tipo_efecto: str
    duracion: int
    origen_jugador_id: str
    bloquea_hacia: Optional[str] = None

# JSONB Mapa
class TerritorioBase(BaseModel):
    owner_id: str
    units: int = Field(ge=0, description="Número de tropas. No puede ser negativo.")
    estado_bloqueo: Optional[str] = None
    efectos: List[EfectoActivo] = Field(default_factory=list)

class JugadorBase(BaseModel):
    numero_jugador: int = Field(default=1, ge=1, le=4)
    tropas_reserva: int = Field(default=0, ge=0)
    movimiento_conquista_pendiente: bool = Field(default=False)
    origen_conquista: Optional[str] = None
    destino_conquista: Optional[str] = None
    
    monedas: int = Field(default=0, ge=0)
    territorio_trabajando: Optional[str] = None
    territorio_investigando: Optional[str] = None
    habilidad_investigando: Optional[str] = None

    tecnologias_predesbloqueadas: List[str] = Field(default_factory=list)
    tecnologias_compradas: List[str] = Field(default_factory=list)
    bajas_causadas: int = Field(default=0)
    historial_conquistas: Dict[str, int] = Field(default_factory=dict)
    regiones_dominadas: List[str] = Field(default_factory=list)
    efectos: List[EfectoActivo] = Field(default_factory=list)

    ha_lanzado_especial: bool = Field(default=False)