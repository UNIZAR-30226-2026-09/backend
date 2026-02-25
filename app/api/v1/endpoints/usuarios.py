from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from app.db.session import get_db
from app.models.usuario import User
from app.schemas.usuario import UserCreate, UserRead, Token
from app.core.security import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter()


# RUTA 1: REGISTRO

@router.post("/registro", response_model=UserRead)
async def registrar_usuario(usuario_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Miramos si el nick ya existe
    query = select(User).where(User.username == usuario_in.username)
    resultado = await db.execute(query)
    if resultado.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este nombre de usuario ya está pillado")
        
    # Miramos si el correo ya existe
    query_email = select(User).where(User.email == usuario_in.email)
    resultado_email = await db.execute(query_email)
    if resultado_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    # Pasamos la contraseña por la trituradora
    contra_hasheada = get_password_hash(usuario_in.password)

    # Creamos el usuario con la contraseña ya cifrada
    nuevo_usuario = User(
        username=usuario_in.username,
        email=usuario_in.email,
        passwd_hash=contra_hasheada 
    )

    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)

    return nuevo_usuario



# RUTA 2: LOGIN

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Buscamos al usuario por su nombre
    query = select(User).where(User.username == form_data.username)
    resultado = await db.execute(query)
    usuario = resultado.scalar_one_or_none()

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
    
    # Pillamos los datos del usuario en la base de datos
    query = select(User).where(User.username == username)
    resultado = await db.execute(query)
    usuario = resultado.scalar_one_or_none()
    
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return usuario


# La ruta en sí. Fíjate que exige pasar por el portero (obtener_usuario_actual)
@router.get("/me", response_model=UserRead)
async def leer_mi_perfil(usuario_actual: User = Depends(obtener_usuario_actual)):
    # Devolvemos el usuario y Pydantic se encarga de no mostrar la contraseña
    return usuario_actual