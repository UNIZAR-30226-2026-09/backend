import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

# Configuracion del JWT (luego moveremos la clave al .env)
SECRET_KEY = "super_clave_secreta_soberania_cambiar_en_produccion" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # La pulsera VIP dura 1 semana

def get_password_hash(password: str) -> str:
    # Trituramos la clave metiendole "sal" para que el churro sea indescifrable
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Comprueba si la clave que mete el user al hacer login coincide con la guardada
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password=password_byte_enc, hashed_password=hashed_password_byte_enc)

def create_access_token(subject: str) -> str:
    # Fabricamos el token JWT con la fecha de caducidad y el usuario (subject)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Firmamos el token con nuestra clave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt