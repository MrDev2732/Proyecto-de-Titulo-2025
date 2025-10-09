"""
Módulo de seguridad para JWT, encriptación de contraseñas y tokens.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from uuid import UUID
import secrets
import string

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.logging import get_logger
from src.database import now_chile
from src.schemas import TokenData


logger = get_logger(__name__)
# Configuración para encriptación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar si una contraseña en texto plano coincide con el hash.

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña almacenada

    Returns:
        bool: True si las contraseñas coinciden
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_password(length: int = 12) -> str:
    """
    Generar una contraseña aleatoria y segura.

    Args:
        length: Longitud de la contraseña (mínimo 8)

    Returns:
        str: Contraseña generada
    """
    if length < 8:
        length = 8

    # Definir caracteres permitidos
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*"

    # Asegurar al menos un carácter de cada tipo
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]

    # Completar el resto de la contraseña
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # Mezclar la contraseña
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def get_password_hash(password: str) -> str:
    """
    Generar hash de una contraseña.

    Args:
        password: Contraseña en texto plano

    Returns:
        str: Hash de la contraseña
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear token de acceso JWT.

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        str: Token JWT
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.api.access_token_expire_minutes
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode, 
        settings.api.secret_key, 
        algorithm=settings.api.algorithm
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear token de refresh JWT.

    Args:
        data: Datos a incluir en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        str: Token JWT de refresh
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.api.refresh_token_expire_days
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode, 
        settings.api.secret_key, 
        algorithm=settings.api.algorithm
    )

    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """
    Verificar y decodificar un token JWT.

    Args:
        token: Token JWT a verificar
        expected_type: Tipo de token esperado ("access" o "refresh")

    Returns:
        TokenData: Datos decodificados del token o None si es inválido
    """
    try:
        payload = jwt.decode(
            token, 
            settings.api.secret_key, 
            algorithms=[settings.api.algorithm]
        )

        logger.info(f"🔍 JWT decodificado exitosamente: {list(payload.keys())}")

        # Verificar el tipo de token
        token_type: str = payload.get("token_type")
        if token_type != expected_type:
            logger.warning(f"❌ Tipo de token incorrecto: esperado '{expected_type}', obtenido '{token_type}'")
            return None
 
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        roles: list = payload.get("roles", [])

        if user_id is None:
            logger.warning(f"❌ No se encontró 'sub' en el payload: {list(payload.keys())}")
            return None

        logger.info(f"✅ Token válido para usuario: {email}")

        token_data = TokenData(
            user_id=user_id,
            email=email,
            roles=roles,
            token_type=token_type
        )

        return token_data

    except JWTError as e:
        logger.error(f"❌ Error JWT: {str(e)}")
        return None


def create_user_tokens(user_id: Union[str, UUID], email: str, roles: list) -> Dict[str, Any]:
    """
    Crear tokens de acceso y refresh para un usuario.

    Args:
        user_id: ID del usuario
        email: Email del usuario
        roles: Lista de roles del usuario

    Returns:
        Dict con access_token, refresh_token y expires_in
    """
    # Convertir UUID a string si es necesario
    if isinstance(user_id, UUID):
        user_id = str(user_id)

    # Datos base para los tokens
    token_data = {
        "sub": user_id,
        "email": email,
        "roles": roles
    }

    # Crear tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.api.access_token_expire_minutes * 60,  # En segundos
        "token_type": "bearer"
    }


def hash_token(token: str) -> str:
    """
    Crear hash SHA256 de un token para almacenamiento seguro.

    Args:
        token: Token JWT a hashear

    Returns:
        str: Hash SHA256 del token
    """
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def create_user_tokens_with_session(
    user_id: UUID, 
    email: str, 
    roles: list[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crear tokens para usuario incluyendo información de sesión.

    Args:
        user_id: ID del usuario
        email: Email del usuario
        roles: Lista de roles del usuario
        ip_address: Dirección IP del cliente
        user_agent: User agent del cliente

    Returns:
        Dict: Diccionario con tokens, hashes y metadatos de sesión
    """
    # Datos para el token
    token_data = {
        "sub": str(user_id),
        "email": email,
        "roles": roles
    }

    # Crear tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # Crear hashes de los tokens
    access_token_hash = hash_token(access_token)
    refresh_token_hash = hash_token(refresh_token)

    # Calcular expiración (usamos la del access token como referencia para la sesión)
    expires_at = now_chile() + timedelta(minutes=settings.api.access_token_expire_minutes)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "access_token_hash": access_token_hash,
        "refresh_token_hash": refresh_token_hash,
        "expires_at": expires_at,
        "expires_in": settings.api.access_token_expire_minutes * 60,  # En segundos
        "token_type": "bearer",
        "ip_address": ip_address,
        "user_agent": user_agent
    }
