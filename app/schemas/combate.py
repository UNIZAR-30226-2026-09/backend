from typing import List
from pydantic import BaseModel, Field

class ResultadoCombate(BaseModel):
    dados_atacante: List[int]
    dados_defensor: List[int]
    bajas_atacante: int
    bajas_defensor: int
    victoria_atacante: bool
    tropas_restantes_defensor: int


class AtaqueCreate(BaseModel):
    territorio_origen_id: str
    territorio_destino_id: str
    tropas_a_mover: int


class MovimientoConquistaCreate(BaseModel):
    tropas_a_mover: int = Field(ge=0, description="Número de tropas adicionales a mover")


class MoverConquistaOut(BaseModel):
    mensaje: str

class PasarFaseOut(BaseModel):
    mensaje: str
    nueva_fase: str
    turno_de: str

class ColocarTropasOut(BaseModel):
    mensaje: str
    reserva_restante: int