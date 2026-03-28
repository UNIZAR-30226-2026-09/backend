from pydantic import BaseModel, Field

class AtaqueCreate(BaseModel):
    territorio_origen_id: str
    territorio_destino_id: str

class ResultadoAtaqueCompleto(BaseModel):
    victoria_atacante: bool
    bajas_atacante: int
    bajas_defensor: int
    tropas_restantes_origen: int
    tropas_restantes_defensor: int

class MovimientoConquistaCreate(BaseModel):
    tropas_a_mover: int = Field(ge=0, description="Número de tropas adicionales a mover")

class MoverConquistaIn(BaseModel):
    tropas: int

class MoverConquistaOut(BaseModel):
    mensaje: str

class PasarFaseOut(BaseModel):
    mensaje: str
    nueva_fase: str
    turno_de: str

class ColocarTropasIn(BaseModel):
    territorio_id: str
    tropas: int

class ColocarTropasOut(BaseModel):
    mensaje: str
    reserva_restante: int