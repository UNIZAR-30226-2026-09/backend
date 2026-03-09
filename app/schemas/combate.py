from typing import List
from pydantic import BaseModel

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