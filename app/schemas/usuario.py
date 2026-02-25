from pydantic import BaseModel, EmailStr, Field
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
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    # Todo opcional por si el calvo solo quiere cambiar el email
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

 
# ESTADÍSTICAS
 
class EstadisticaRead(BaseModel):
    # Solo lectura, esto se actualiza internamente en el backend tras cada partida
    nombre_user: str
    num_partidas_jugadas: int
    num_partidas_ganadas: int
    num_continentes_conquistados: int
    num_soldados_matados: int

    class Config:
        from_attributes = True

 
# AMISTADES
 
class AmistadCreate(BaseModel):
    # Cuando mandas una solicitud, solo necesitas decir a quién se la mandas
    user_2: str

class AmistadRead(BaseModel):
    user_1: str
    user_2: str
    estado: EstadoAmistad

    class Config:
        from_attributes = True