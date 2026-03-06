from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.schemas.usuario import AmistadCreate, AmistadRead
from app.models.usuario import Amistad, EstadoAmistad, User
from app.api.v1.endpoints.usuarios import obtener_usuario_actual
from app.db.session import get_db

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
    query_user = select(User).where(User.username == amistad_in.user_2)
    res_user = await db.execute(query_user)
    if not res_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="El usuario al que intentas agregar no existe")

    # Comprobar si ya existe relación
    query_amistad = select(Amistad).where(
        or_(
            and_(Amistad.user_1 == usuario_actual.username, Amistad.user_2 == amistad_in.user_2),
            and_(Amistad.user_1 == amistad_in.user_2, Amistad.user_2 == usuario_actual.username)
        )
    )
    res_amistad = await db.execute(query_amistad)
    if res_amistad.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe una relación o solicitud pendiente con este usuario")

    # Todo limpio, creamos solicitud
    nueva_amistad = Amistad(
        user_1=usuario_actual.username,
        user_2=amistad_in.user_2,
        estado=EstadoAmistad.PENDIENTE
    )
    
    db.add(nueva_amistad)
    await db.commit()
    await db.refresh(nueva_amistad)

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
    query = select(Amistad).where(
        Amistad.user_2 == usuario_actual.username,
        Amistad.estado == EstadoAmistad.PENDIENTE
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()

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
    query = select(Amistad).where(
        Amistad.user_1 == username_solicitante,
        Amistad.user_2 == usuario_actual.username,
        Amistad.estado == EstadoAmistad.PENDIENTE
    )
    resultado = await db.execute(query)
    amistad = resultado.scalar_one_or_none()

    if not amistad:
        raise HTTPException(status_code=404, detail="No hay ninguna solicitud pendiente de este usuario")

    # Le cambiamos el estado
    amistad.estado = EstadoAmistad.ACEPTADA
    await db.commit()
    await db.refresh(amistad)

    return amistad

# ----------------------------------------------------------------------------
# 4. VER MI LISTA DE AMIGOS
# ----------------------------------------------------------------------------
@router.get("", response_model=list[AmistadRead])
async def listar_amigos(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    # Buscamos donde salga yo (ya sea como user_1 o user_2) y el estado sea aceptada
    query = select(Amistad).where(
        or_(Amistad.user_1 == usuario_actual.username, Amistad.user_2 == usuario_actual.username),
        Amistad.estado == EstadoAmistad.ACEPTADA
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()