from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Importamos la conexión a la BD, el modelo de tabla y los esquemas
from app.db.session import get_db
from app.models.usuario import User
from app.schemas.usuario import UserCreate, UserRead

router = APIRouter()

@router.post("/registro", response_model=UserRead)
async def registrar_usuario(usuario_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Miramos si ya hay alguien con ese nombre de usuario en Neon
    query = select(User).where(User.username == usuario_in.username)
    resultado = await db.execute(query)
    usuario_existente = resultado.scalar_one_or_none()
    
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está pillado")
        
    # Hacemos lo mismo para comprobar que el email no esté repetido
    query_email = select(User).where(User.email == usuario_in.email)
    resultado_email = await db.execute(query_email)
    email_existente = resultado_email.scalar_one_or_none()
    
    if email_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Si todo está libre, preparamos el usuario para guardarlo.
    # De momento guardamos la contraseña tal cual para ir probando.
    # Más adelante meteremos una librería para encriptarla (hashearla).
    nuevo_usuario = User(
        username=usuario_in.username,
        email=usuario_in.email,
        passwd_hash=usuario_in.password 
    )

    # Lo metemos en la base de datos y guardamos los cambios
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)

    # FastAPI devuelve el usuario. Como le hemos puesto response_model=UserRead,
    # el solo se encarga de borrar la contraseña antes de mandarlo por internet.
    return nuevo_usuario