from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.usuario import AmistadCreate, AmistadRead
from app.models.usuario import User
from app.api.deps import obtener_usuario_actual
from app.db.session import get_db
from app.crud import crud_amigos

router = APIRouter()

# ----------------------------------------------------------------------------
# 1. SOLICITAR AMISTAD
# ----------------------------------------------------------------------------
@router.post("/solicitar", response_model=AmistadRead)
async def solicitar_amistad(
    amistad_in: AmistadCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Evitar que uno se añada a sí mismo
    if usuario_actual.username == amistad_in.user_2:
        raise HTTPException(status_code=400, detail="No puedes enviarte una solicitud a ti mismo")

    # Mirar si el usuario existe
    if not await crud_amigos.verificar_usuario_existe(db, amistad_in.user_2):
        raise HTTPException(status_code=404, detail="El usuario al que intentas agregar no existe")

    # Comprobar si ya existe relación
    relacion_existente = await crud_amigos.obtener_relacion_existente(
        db, 
        usuario_actual.username, 
        amistad_in.user_2
    )
    if relacion_existente:
        raise HTTPException(status_code=400, detail="Ya existe una relación o solicitud pendiente con este usuario")

    # Todo limpio, creamos solicitud
    nueva_amistad = await crud_amigos.crear_solicitud(
        db,
        usuario_actual.username,
        amistad_in.user_2
    )

    return nueva_amistad

# ----------------------------------------------------------------------------
# 2. VER MIS SOLICITUDES PENDIENTES
# ----------------------------------------------------------------------------
@router.get("/solicitudes", response_model=list[AmistadRead])
async def ver_solicitudes(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos las que me han mandado a mí (yo soy el user_2) y están pendientes
    return await crud_amigos.obtener_solicitudes_pendientes(db, usuario_actual.username)

# ----------------------------------------------------------------------------
# 3. ACEPTAR AMISTAD
# ----------------------------------------------------------------------------
@router.put("/{username_solicitante}/aceptar", response_model=AmistadRead)
async def aceptar_amistad(
    username_solicitante: str,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos la solicitud específica
    amistad = await crud_amigos.obtener_solicitud_especifica(
        db,
        username_solicitante,
        usuario_actual.username
    )

    if not amistad:
        raise HTTPException(status_code=404, detail="No hay ninguna solicitud pendiente de este usuario")

    # Aceptamos la solicitud
    amistad_aceptada = await crud_amigos.aceptar_solicitud(db, amistad)

    return amistad_aceptada

# ----------------------------------------------------------------------------
# 4. VER MI LISTA DE AMIGOS
# ----------------------------------------------------------------------------
@router.get("", response_model=list[AmistadRead])
async def listar_amigos(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos donde salga yo (ya sea como user_1 o user_2) y el estado sea aceptada
    return await crud_amigos.obtener_lista_amigos(db, usuario_actual.username)