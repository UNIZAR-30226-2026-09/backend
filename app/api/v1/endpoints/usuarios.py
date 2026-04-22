from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.usuario import User
from app.schemas.usuario import UserCreate, UserRead, Token, UserUpdate, EstadisticaRead
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import obtener_usuario_actual
from app.crud import crud_usuario, crud_estadisticas

router = APIRouter()


# --- AUTENTICACIÓN ---

@router.post("/registro", response_model=UserRead)
async def registrar_usuario(usuario_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Crea una nueva cuenta de usuario.

    - **usuario_in**: Esquema con los datos requeridos para el registro (email, username, password).
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna los datos del usuario recién creado.
    """
    
    usuario_existente = await crud_usuario.get_user_by_username(db, usuario_in.username)
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está pillado")
        
    email_existente = await crud_usuario.get_user_by_email(db, usuario_in.email)
    if email_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    contra_hasheada = get_password_hash(usuario_in.password)

    nuevo_usuario = await crud_usuario.crear_usuario(db, usuario_in, contra_hasheada)
    
    await crud_estadisticas.inicializar_estadisticas(db, usuario_in.username)
    
    return nuevo_usuario


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Inicia sesión y devuelve los tokens JWT correspondientes.

    - **form_data**: Formulario OAuth2 que incluye el identificador (username o email) y la contraseña.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el token de acceso JWT y el tipo de token (bearer).
    """

    usuario = await crud_usuario.get_user_by_username(db, form_data.username)

    # Si no existe o la contraseña no cuadra con la de Neon, fuera
    if not usuario or not verify_password(form_data.password, usuario.passwd_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_vip = create_access_token(subject=usuario.username)
    
    return {"access_token": token_vip, "token_type": "bearer"}



# --- USUARIOS ---

@router.get("/me", response_model=UserRead)
async def leer_mi_perfil(usuario_actual: User = Depends(obtener_usuario_actual)):
    """
    Obtiene el perfil del usuario autenticado actual.

    - **usuario_actual**: Dependencia que extrae y valida el usuario actual basado en su token JWT.
    
    Retorna la información del perfil del usuario sin datos sensibles.
    """
    
    return usuario_actual

@router.put("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def actualizar_perfil_actual(
    usuario_in: UserUpdate, 
    usuario_actual: User = Depends(obtener_usuario_actual), 
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza la información del perfil del usuario autenticado.

    - **usuario_in**: Esquema con los campos a modificar (ej. avatar_url, email).
    - **usuario_actual**: Dependencia que valida el usuario actual autenticado.
    - **db**: Sesión de base de datos asíncrona.
    
    Retorna el perfil del usuario actualizado.
    """
    raise HTTPException(status_code=501, detail="No implementado")