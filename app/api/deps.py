from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.db.session import get_db
from app.models.usuario import User
from app.core.security import SECRET_KEY, ALGORITHM
from app.crud import crud_usuario

# Indicamos a Swagger dónde se pide el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/usuarios/login")

# Función que hace de portero: lee el token y saca el usuario
async def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        # Desencriptamos el token con la misma clave secreta
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="No se pudo validar el token")
    
    # Pillamos los datos del usuario en la base de datos usando el CRUD
    usuario = await crud_usuario.get_user_by_username(db, username)
    
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return usuario
