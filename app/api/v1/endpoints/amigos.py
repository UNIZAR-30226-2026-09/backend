from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.usuario import UserRead, AmistadCreate, AmistadRead, AmistadUpdate, AmigoActivoRead
from app.models.usuario import User, Amistad, EstadoAmistad
from app.api.deps import obtener_usuario_actual
from app.db.session import get_db
from app.crud import crud_amigos
from app.core.ws_manager import manager

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

    if amistad_in.user_2 in manager.global_connections:
        await manager.global_connections[amistad_in.user_2].send_json({
            "tipo_evento": "NUEVA_SOLICITUD_AMISTAD",
            "de": usuario_actual.username
        })

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

    query = select(Amistad).where(Amistad.id == solicitud_id)
    result = await db.execute(query)
    solicitud = result.scalar_one_or_none()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.user_2 != usuario_actual.username:
        raise HTTPException(status_code=403, detail="No tienes permiso para procesar esta solicitud")

    if estado_in.estado == EstadoAmistad.ACEPTADA:
        return await crud_amigos.aceptar_solicitud(db, solicitud)
    
    elif estado_in.estado == EstadoAmistad.RECHAZADA:
        await crud_amigos.rechazar_solicitud(db, solicitud)
        return solicitud 
    
    raise HTTPException(status_code=400, detail="Estado no válido")

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
    query = select(Amistad).where(Amistad.id == amigo_id)
    result = await db.execute(query)
    amistad = result.scalar_one_or_none()

    if not amistad:
        raise HTTPException(status_code=404, detail="Amigo no encontrado")

    if usuario_actual.username not in [amistad.user_1, amistad.user_2]:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta amistad")

    await crud_amigos.eliminar_amigo(db, amistad)
    return None

@router.get("/activos", response_model=list[AmigoActivoRead])
async def listar_amigos_activos(
    usuario_actual: User = Depends(obtener_usuario_actual),
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve la lista de amigos aceptados junto con su estado de conexión en tiempo real
    (EN_PARTIDA, CONECTADO, DESCONECTADO).
    """
    # Obtenemos la lista base de amigos (los que están ACEPTADOS)
    amigos_db = await crud_amigos.obtener_lista_amigos(db, usuario_actual.username)
    
    amigos_activos = []
    
    # Iteramos sobre las amistades para sacar el nombre del amigo
    for relacion in amigos_db:
        nombre_amigo = relacion.user_2 if relacion.user_1 == usuario_actual.username else relacion.user_1
        
        estado = manager.obtener_estado_conexion(nombre_amigo)
        user = await db.get(User, nombre_amigo)

        amigos_activos.append(
            AmigoActivoRead(
                username=nombre_amigo,
                estado_conexion=estado,
                avatar=user.avatar if user else "/static/perfiles/default.png"
            )
        )
        
    return amigos_activos