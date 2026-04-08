from pydantic import BaseModel, Field
from typing import Dict, List, Optional

# JSONB Mapa
class TerritorioBase(BaseModel):
    owner_id: str
    units: int = Field(ge=0, description="Número de tropas. No puede ser negativo.")
    estado_bloqueo: Optional[str] = None

class JugadorBase(BaseModel):
    numero_jugador: int = Field(default=1, ge=1, le=4)
    tropas_reserva: int = Field(default=0, ge=0)
    movimiento_conquista_pendiente: bool = Field(default=False)
    origen_conquista: Optional[str] = None
    destino_conquista: Optional[str] = None
    
    monedas: int = Field(default=0, ge=0)
    territorio_trabajando: Optional[str] = None
    territorio_investigando: Optional[str] = None
    rama_investigando: Optional[str] = None

    nivel_ramas: Dict[str, int] = Field(default_factory=lambda: {
        "biologica": 0,
        "logistica": 0,
        "artilleria": 0
    })

    tecnologias_predesbloqueadas: List[str] = Field(default_factory=list)
    tecnologias_compradas: List[str] = Field(default_factory=list)