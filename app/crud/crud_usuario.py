from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.models.usuario import User
from app.schemas.usuario import UserCreate

# ----------------------------------------------------------------------------
# 1. OBTENER USUARIO POR USERNAME
# ----------------------------------------------------------------------------
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Busca un usuario por su nombre de usuario.
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario a buscar
        
    Returns:
        Objeto User si existe, None en caso contrario
    """
    query = select(User).where(User.username == username)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 2. OBTENER USUARIO POR EMAIL
# ----------------------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Busca un usuario por su correo electrónico.
    
    Args:
        db: Sesión de base de datos
        email: Correo electrónico a buscar
        
    Returns:
        Objeto User si existe, None en caso contrario
    """
    query = select(User).where(User.email == email)
    resultado = await db.execute(query)
    return resultado.scalar_one_or_none()

# ----------------------------------------------------------------------------
# 3. CREAR USUARIO
# ----------------------------------------------------------------------------
async def crear_usuario(
    db: AsyncSession, 
    usuario_in: UserCreate, 
    contra_hasheada: str
) -> User:
    """
    Crea un nuevo usuario en la base de datos.
    Esta función recibe el hash de la contraseña ya generado desde la API.
    
    Args:
        db: Sesión de base de datos
        usuario_in: Datos del usuario (username, email, password sin hashear)
        contra_hasheada: Hash de la contraseña ya generado
        
    Returns:
        Objeto User creado y refrescado
    """
    nuevo_usuario = User(
        username=usuario_in.username,
        email=usuario_in.email,
        passwd_hash=contra_hasheada 
    )

    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)

    return nuevo_usuario
