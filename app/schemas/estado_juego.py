from pydantic import BaseModel, Field
from typing import Dict, Optional

# JSONB Mapa
class TerritorioBase(BaseModel):
    owner_id: str
    units: int = Field(ge=0, description="Número de tropas. No puede ser negativo.")

class JugadorBase(BaseModel):
    tropas_reserva: int = Field(default=0, ge=0)
    movimiento_conquista_pendiente: bool = Field(default=False)
    origen_conquista: Optional[str] = None
    destino_conquista: Optional[str] = None