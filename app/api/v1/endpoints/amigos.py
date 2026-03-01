from fastapi import APIRouter, Depends
from app.schemas.usuario import AmistadCreate, AmistadRead
from app.models.usuario import EstadoAmistad, User
from app.api.v1.endpoints.usuarios import obtener_usuario_actual

router = APIRouter()

@router.post("/solicitar", response_model=AmistadRead)
async def solicitar_amistad(
    amistad_in: AmistadCreate,
    usuario_actual: User = Depends(obtener_usuario_actual)
):
    # TODO: Guardar la relación en la base de datos.
    return AmistadRead(
        user_1=usuario_actual.username,
        user_2=amistad_in.user_2,
        estado=EstadoAmistad.PENDIENTE
    )