from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from typing import Optional

from app.models.usuario import User, Amistad, EstadoAmistad

# ----------------------------------------------------------------------------
# 1. VERIFICAR SI UN USUARIO EXISTE
# ----------------------------------------------------------------------------
async def verificar_usuario_existe(db: AsyncSession, username: str) -> bool:
    """
    Comprueba si un usuario existe en la tabla User.
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario a verificar
        
    Returns:
        True si el usuario existe, False en caso contrario
    """
    query = select(User).where(User.username == username)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none() is not None

# ----------------------------------------------------------------------------
# 2. OBTENER RELACIÓN EXISTENTE
# ----------------------------------------------------------------------------
async def obtener_relacion_existente(
    db: AsyncSession, 
    user_1: str, 
    user_2: str
) -> Optional[Amistad]:
    """
    Comprueba si ya existe una relación (pendiente o aceptada) entre dos usuarios.
    
    Args:
        db: Sesión de base de datos
        user_1: Primer usuario
        user_2: Segundo usuario
        
    Returns:
        Objeto Amistad si existe una relación, None en caso contrario
    """
    query = select(Amistad).where(
        or_(
            and_(Amistad.user_1 == user_1, Amistad.user_2 == user_2),
            and_(Amistad.user_1 == user_2, Amistad.user_2 == user_1)
        )
    )
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 3. CREAR SOLICITUD DE AMISTAD
# ----------------------------------------------------------------------------
async def crear_solicitud(
    db: AsyncSession, 
    user_1: str, 
    user_2: str
) -> Amistad:
    """
    Crea el objeto Amistad en estado PENDIENTE, hace add, commit y refresh.
    
    Args:
        db: Sesión de base de datos
        user_1: Usuario que envía la solicitud
        user_2: Usuario que recibe la solicitud
        
    Returns:
        Objeto Amistad creado y refrescado
    """
    nueva_amistad = Amistad(
        user_1=user_1,
        user_2=user_2,
        estado=EstadoAmistad.PENDIENTE
    )
    
    db.add(nueva_amistad)
    await db.commit()
    await db.refresh(nueva_amistad)
    
    return nueva_amistad

# ----------------------------------------------------------------------------
# 4. OBTENER SOLICITUDES PENDIENTES
# ----------------------------------------------------------------------------
async def obtener_solicitudes_pendientes(
    db: AsyncSession, 
    username: str
) -> list[Amistad]:
    """
    Devuelve la lista de solicitudes donde user_2 es el username y el estado es PENDIENTE.
    
    Args:
        db: Sesión de base de datos
        username: Usuario que recibió las solicitudes
        
    Returns:
        Lista de amistades pendientes
    """
    query = select(Amistad).where(
        Amistad.user_2 == username,
        Amistad.estado == EstadoAmistad.PENDIENTE
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()

# ----------------------------------------------------------------------------
# 5. OBTENER SOLICITUD ESPECÍFICA
# ----------------------------------------------------------------------------
async def obtener_solicitud_especifica(
    db: AsyncSession, 
    solicitante: str, 
    receptor: str
) -> Optional[Amistad]:
    """
    Busca una solicitud PENDIENTE exacta entre user_1 y user_2.
    
    Args:
        db: Sesión de base de datos
        solicitante: Usuario que envió la solicitud (user_1)
        receptor: Usuario que recibió la solicitud (user_2)
        
    Returns:
        Objeto Amistad si existe la solicitud, None en caso contrario
    """
    query = select(Amistad).where(
        Amistad.user_1 == solicitante,
        Amistad.user_2 == receptor,
        Amistad.estado == EstadoAmistad.PENDIENTE
    )
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 6. ACEPTAR SOLICITUD DE AMISTAD
# ----------------------------------------------------------------------------
async def aceptar_solicitud(db: AsyncSession, amistad: Amistad) -> Amistad:
    """
    Cambia el estado de la amistad a ACEPTADA, hace commit y refresh.
    
    Args:
        db: Sesión de base de datos
        amistad: Objeto Amistad a aceptar
        
    Returns:
        Objeto Amistad actualizado y refrescado
    """
    amistad.estado = EstadoAmistad.ACEPTADA
    await db.commit()
    await db.refresh(amistad)
    
    return amistad

# ----------------------------------------------------------------------------
# 7. OBTENER LISTA DE AMIGOS
# ----------------------------------------------------------------------------
async def obtener_lista_amigos(db: AsyncSession, username: str) -> list[Amistad]:
    """
    Devuelve la lista de amistades ACEPTADAS donde el username sea user_1 o user_2.
    
    Args:
        db: Sesión de base de datos
        username: Usuario del cual queremos obtener los amigos
        
    Returns:
        Lista de amistades aceptadas
    """
    query = select(Amistad).where(
        or_(Amistad.user_1 == username, Amistad.user_2 == username),
        Amistad.estado == EstadoAmistad.ACEPTADA
    )
    resultado = await db.execute(query)
    return resultado.scalars().all()
