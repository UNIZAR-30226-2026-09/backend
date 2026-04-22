from pydantic import computed_field, BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from app.models.usuario import EstadoAmistad # Pillamos el enum directamente del modelo

 
# USUARIOS
 
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr 

class UserCreate(UserBase):
    # Pedimos la pass solo al registrarse
    password: str = Field(..., min_length=6) 

class UserRead(UserBase):
    # Lo que devolvemos al frontend (sin la contraseña)
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    # Todo opcional por si el calvo solo quiere cambiar el email
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

 
# ESTADÍSTICAS
 
class EstadisticaRead(BaseModel):
    nombre_user: str
    num_partidas_jugadas: int
    num_partidas_ganadas: int
    num_continentes_conquistados: int
    num_regiones_conquistadas: int
    num_soldados_matados: int
    conquistas_por_region: dict  = Field(exclude=True)

    @computed_field
    @property
    def winrate(self) -> float:
        if self.num_partidas_jugadas == 0:
            return 0.0
        return round((self.num_partidas_ganadas / self.num_partidas_jugadas) * 100, 2)


    @computed_field
    @property
    def region_mas_conquistada(self) -> str | None:
        if not self.conquistas_por_region:
            return None
        return max(self.conquistas_por_region, key=self.conquistas_por_region.get)

    model_config = ConfigDict(from_attributes=True)

class RankingItemOut(BaseModel):
    nombre_user: str
    num_partidas_ganadas: int

    model_config = ConfigDict(from_attributes=True)

 
# AMISTADES
 
class AmistadCreate(BaseModel):
    # Cuando mandas una solicitud, solo necesitas decir a quién se la mandas
    user_2: str

class AmistadRead(BaseModel):
    id: int
    user_1: str
    user_2: str
    estado: EstadoAmistad

    model_config = ConfigDict(from_attributes=True)


class AmistadUpdate(BaseModel):
    estado: EstadoAmistad

# TOKENS VIP (JWT)

class Token(BaseModel):
    access_token: str
    token_type: str