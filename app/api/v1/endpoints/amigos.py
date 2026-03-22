from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.usuario import UserRead, AmistadCreate, AmistadRead, AmistadUpdate
from app.models.usuario import User
from app.api.deps import obtener_usuario_actual
from app.db.session import get_db
from app.crud import crud_amigos

router = APIRouter()

# --- AMISTADES ---
@router.get("", response_model=list[AmistadRead])
async def listar_amigos(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos los amigos aceptados del usuario autenticado.

    - **usuario_actual**: Dependencia que valida el usuario actual autenticado mediante JWT.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna una lista de objetos de usuario correspondientes a los amigos confirmados.
    """
    return await crud_amigos.obtener_lista_amigos(db, usuario_actual.username)


@router.post("/solicitar", response_model=AmistadRead)
async def enviar_solicitud_amistad(
    amistad_in: AmistadCreate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Envía una solicitud de amistad a otro jugador.

    - **amistad_in**: Esquema con los datos del destinatario de la solicitud.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el estado de la solicitud de amistad recién creada.
    """
    # Evitar que uno se añada a sí mismo
    if usuario_actual.username == amistad_in.user_2:
        raise HTTPException(status_code=400, detail="No puedes enviarte una solicitud a ti mismo")

    # Mirar si el usuario existe
    if not await crud_amigos.verificar_usuario_existe(db, amistad_in.user_2):
        raise HTTPException(status_code=404, detail="El usuario al que intentas agregar no existe")

    relacion_existente = await crud_amigos.obtener_relacion_existente(
        db, 
        usuario_actual.username, 
        amistad_in.user_2
    )
    if relacion_existente:
        raise HTTPException(status_code=400, detail="Ya existe una relación o solicitud pendiente con este usuario")

    nueva_amistad = await crud_amigos.crear_solicitud(
        db,
        usuario_actual.username,
        amistad_in.user_2
    )

    return nueva_amistad

@router.get("/solicitudes", response_model=list[AmistadRead])
async def listar_solicitudes_pendientes(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista las solicitudes de amistad pendientes (tanto enviadas como recibidas).

    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna una lista de los objetos de estado de solicitud de amistad.
    """
    return await crud_amigos.obtener_solicitudes_pendientes(db, usuario_actual.username)


@router.put("/solicitudes/{solicitud_id}", response_model=AmistadRead, status_code=status.HTTP_200_OK)
async def procesar_solicitud_amistad(
    solicitud_id: int,
    estado_in: AmistadUpdate,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Acepta o rechaza una solicitud de amistad recibida.

    - **solicitud_id**: Identificador único de la solicitud a procesar.
    - **estado_in**: Esquema que contiene el nuevo estado a aplicar (ACEPTADA o RECHAZADA).
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el objeto de amistad actualizado con el nuevo estado.
    """
    raise HTTPException(status_code=501, detail="No implementado")

# @router.put("/{username_solicitante}/aceptar", response_model=AmistadRead)
# async def aceptar_amistad(
#     username_solicitante: str,
#     usuario_actual: User = Depends(obtener_usuario_actual),
#     db: AsyncSession = Depends(get_db)
# ):
#     # Buscamos la solicitud específica
#     amistad = await crud_amigos.obtener_solicitud_especifica(
#         db,
#         username_solicitante,
#         usuario_actual.username
#     )

#     if not amistad:
#         raise HTTPException(status_code=404, detail="No hay ninguna solicitud pendiente de este usuario")

#     # Aceptamos la solicitud
#     amistad_aceptada = await crud_amigos.aceptar_solicitud(db, amistad)

#     return amistad_aceptada


@router.delete("/{amigo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_amigo(
    amigo_id: int,
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina a un usuario de la lista de amigos.

    - **amigo_id**: Identificador único del amigo que será eliminado de la lista.
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna un código de estado 204 indicando que la eliminación fue exitosa (sin contenido).
    """
    raise HTTPException(status_code=501, detail="No implementado")
