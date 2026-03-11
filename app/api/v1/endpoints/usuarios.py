from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import User
from app.schemas.usuario import UserCreate, UserRead, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import obtener_usuario_actual
from app.crud import crud_usuario

router = APIRouter()


# RUTA 1: REGISTRO

@router.post("/registro", response_model=UserRead)
async def registrar_usuario(usuario_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Miramos si el nick ya existe
    usuario_existente = await crud_usuario.get_user_by_username(db, usuario_in.username)
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está pillado")
        
    # Miramos si el correo ya existe
    email_existente = await crud_usuario.get_user_by_email(db, usuario_in.email)
    if email_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Pasamos la contraseña por la trituradora
    contra_hasheada = get_password_hash(usuario_in.password)

    # Creamos el usuario usando el CRUD
    nuevo_usuario = await crud_usuario.crear_usuario(db, usuario_in, contra_hasheada)

    return nuevo_usuario



# RUTA 2: LOGIN

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Buscamos al usuario por su nombre usando el CRUD
    usuario = await crud_usuario.get_user_by_username(db, form_data.username)

    # Si no existe o la contraseña no cuadra con la de Neon, fuera
    if not usuario or not verify_password(form_data.password, usuario.passwd_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Le fabricamos el token con su nombre
    token_vip = create_access_token(subject=usuario.username)
    
    return {"access_token": token_vip, "token_type": "bearer"}



# RUTA 3: PERFIL PROTEGIDO

# La ruta en sí. Fíjate que exige pasar por el portero (obtener_usuario_actual)
@router.get("/me", response_model=UserRead)
async def leer_mi_perfil(usuario_actual: User = Depends(obtener_usuario_actual)):
    # Devolvemos el usuario y Pydantic se encarga de no mostrar la contraseña
    return usuario_actual