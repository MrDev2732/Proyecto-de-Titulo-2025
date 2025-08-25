"""
Utilidades de seguridad para autenticación
Funciones para rate limiting, detección de ataques y análisis de riesgo usando ORM.
"""

from typing import Dict, Optional, Tuple, NamedTuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.auth_log_repository import AuthenticationLogRepository
from src.core.logging import get_logger


logger = get_logger(__name__)


class SecurityMetrics(NamedTuple):
    """Métricas de seguridad estructuradas."""
    ip_failures: int
    email_failures: int
    risk_score: int
    ip_rate_limited: bool
    email_rate_limited: bool
    velocity_score: int
    geo_risk: int


class AuthSecurityAnalyzer:
    """Analizador de seguridad para eventos de autenticación usando ORM."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = AuthenticationLogRepository()

        # Configuración de umbrales
        self.config = {
            'ip_rate_limit': {'minutes': 10, 'max_failures': 5},
            'email_rate_limit': {'minutes': 15, 'max_failures': 8},
            'risk_thresholds': {
                'captcha': 40,
                'mfa': 60,
                'email_verification': 70,
                'block': 90
            }
        }

    async def check_rate_limit_by_ip(
        self, 
        ip: str, 
        minutes: int = 10, 
        max_failures: int = 5
    ) -> Tuple[bool, int]:
        """
        Verifica rate limiting por IP usando ORM.

        Args:
            ip: Dirección IP a verificar
            minutes: Ventana de tiempo en minutos
            max_failures: Máximo número de fallos permitidos

        Returns:
            Tupla (is_rate_limited, current_failure_count)
        """
        failure_count = await self.repository.count_failures_by_ip(
            self.session, ip, minutes
        )
        is_rate_limited = failure_count >= max_failures

        return is_rate_limited, failure_count

    async def check_rate_limit_by_email(
        self, 
        email: str, 
        minutes: int = 15, 
        max_failures: int = 8
    ) -> Tuple[bool, int]:
        """
        Verifica rate limiting por email usando ORM.

        Args:
            email: Email a verificar
            minutes: Ventana de tiempo en minutos
            max_failures: Máximo número de fallos permitidos

        Returns:
            Tupla (is_rate_limited, current_failure_count)
        """
        failure_count = await self.repository.count_failures_by_email(
            self.session, email, minutes
        )
        is_rate_limited = failure_count >= max_failures

        return is_rate_limited, failure_count

    async def calculate_risk_score(
        self,
        ip: str,
        email: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None
    ) -> int:
        """
        Calcula puntuación de riesgo basada en factores históricos usando ORM.

        Args:
            ip: Dirección IP del intento
            email: Email utilizado (opcional)
            user_agent: User agent del cliente (opcional)
            geo_country: País de origen (opcional)

        Returns:
            Puntuación de riesgo (0-100)
        """
        risk_score = 0

        # Factor 1: Historial de la IP (25 puntos máximo)
        ip_risk = await self._analyze_ip_risk(ip)
        risk_score += min(ip_risk, 25)

        # Factor 2: Historial del email (20 puntos máximo)
        if email:
            email_risk = await self._analyze_email_risk(email)
            risk_score += min(email_risk, 20)

        # Factor 3: Geolocalización sospechosa (20 puntos máximo)
        if geo_country and email:
            geo_risk = await self._analyze_geo_risk(email, geo_country)
            risk_score += min(geo_risk, 20)

        # Factor 4: User agent sospechoso (15 puntos máximo)
        if user_agent:
            ua_risk = self._analyze_user_agent_risk(user_agent)
            risk_score += min(ua_risk, 15)

        # Factor 5: Velocidad de intentos (20 puntos máximo)
        velocity_risk = await self._analyze_velocity_risk(ip, email)
        risk_score += min(velocity_risk, 20)

        return min(risk_score, 100)

    async def _analyze_ip_risk(self, ip: str) -> int:
        """Analiza el riesgo basado en el historial de la IP usando ORM."""
        analysis = await self.repository.get_ip_analysis(self.session, ip, days=7)

        if analysis['total_attempts'] == 0:
            return 0

        risk = 0
        failed_attempts = analysis['failed_attempts']
        unique_emails = analysis['unique_emails']
        failure_rate = analysis['failure_rate']

        # Muchos fallos
        if failed_attempts > 20:
            risk += 15
        elif failed_attempts > 10:
            risk += 10
        elif failed_attempts > 5:
            risk += 5

        # Tasa de fallo alta
        if failure_rate > 80:
            risk += 10
        elif failure_rate > 50:
            risk += 5

        # Muchos emails diferentes (posible ataque)
        if unique_emails > 10:
            risk += 10
        elif unique_emails > 5:
            risk += 5

        return risk

    async def _analyze_email_risk(self, email: str) -> int:
        """Analiza el riesgo basado en el historial del email usando ORM."""
        analysis = await self.repository.get_email_analysis(self.session, email, days=7)

        if analysis['total_attempts'] == 0:
            return 0

        risk = 0
        failed_attempts = analysis['failed_attempts']
        unique_ips = analysis['unique_ips']

        # Muchos fallos recientes
        if failed_attempts > 15:
            risk += 10
        elif failed_attempts > 8:
            risk += 5

        # Muchas IPs diferentes (posible compromiso)
        if unique_ips > 5:
            risk += 10
        elif unique_ips > 3:
            risk += 5

        return risk

    async def _analyze_geo_risk(self, email: str, geo_country: str) -> int:
        """Analiza riesgo basado en cambios geográficos usando ORM."""
        recent_countries = await self.repository.get_recent_countries_for_email(
            self.session, email, days=30, limit=3
        )

        if not recent_countries:
            return 5  # Nuevo usuario, riesgo bajo-medio

        if geo_country not in recent_countries:
            return 15  # País completamente nuevo

        return 0  # País conocido

    def _analyze_user_agent_risk(self, user_agent: str) -> int:
        """Analiza riesgo basado en el user agent."""
        risk = 0

        # User agents sospechosos
        suspicious_patterns = [
            'curl', 'wget', 'python', 'bot', 'crawler', 
            'script', 'automated', 'headless'
        ]

        ua_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if pattern in ua_lower:
                risk += 10
                break

        # User agent muy corto o vacío
        if len(user_agent) < 20:
            risk += 5

        return risk

    async def _analyze_velocity_risk(
        self, 
        ip: str, 
        email: Optional[str] = None
    ) -> int:
        """Analiza riesgo basado en velocidad de intentos usando ORM."""
        recent_attempts = await self.repository.count_recent_attempts(
            self.session, ip=ip, email=email, minutes=5
        )

        # Velocidad alta es sospechosa
        if recent_attempts > 10:
            return 20
        elif recent_attempts > 5:
            return 10
        elif recent_attempts > 3:
            return 5

        return 0

    async def get_security_recommendations(
        self, 
        ip: str, 
        email: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Obtiene recomendaciones de seguridad basadas en el análisis usando ORM.

        Args:
            ip: Dirección IP
            email: Email (opcional)
            user_agent: User agent (opcional)
            geo_country: País de origen (opcional)

        Returns:
            Diccionario con recomendaciones y métricas
        """
        # Verificar rate limits
        ip_limited, ip_failures = await self.check_rate_limit_by_ip(
            ip, **self.config['ip_rate_limit']
        )
        email_limited, email_failures = (False, 0)

        if email:
            email_limited, email_failures = await self.check_rate_limit_by_email(
                email, **self.config['email_rate_limit']
            )

        # Calcular risk score
        risk_score = await self.calculate_risk_score(ip, email, user_agent, geo_country)

        # Calcular velocidad para métricas adicionales
        velocity_score = 0
        if recent_attempts := await self.repository.count_recent_attempts(
            self.session, ip=ip, email=email, minutes=5
        ):
            velocity_score = min(recent_attempts * 10, 50)

        # Crear métricas estructuradas
        metrics = SecurityMetrics(
            ip_failures=ip_failures,
            email_failures=email_failures,
            risk_score=risk_score,
            ip_rate_limited=ip_limited,
            email_rate_limited=email_limited,
            velocity_score=velocity_score,
            geo_risk=await self._analyze_geo_risk(email, geo_country) if email and geo_country else 0
        )

        # Decisiones basadas en umbrales configurables
        thresholds = self.config['risk_thresholds']

        recommendations = {
            'allow_attempt': not (ip_limited or email_limited or risk_score >= thresholds['block']),
            'require_captcha': risk_score >= thresholds['captcha'] or ip_failures > 2,
            'require_mfa': risk_score >= thresholds['mfa'],
            'require_email_verification': risk_score >= thresholds['email_verification'],
            'block_request': risk_score >= thresholds['block'] or ip_limited or email_limited,
            'delay_response': risk_score > 30 or ip_failures > 1,
            'log_high_risk': risk_score >= 80,
            'metrics': metrics._asdict()
        }

        # Logging para monitoreo
        if recommendations['block_request']:
            logger.warning(f"Blocked auth attempt: IP={ip}, email={email}, risk={risk_score}")
        elif recommendations['require_mfa']:
            logger.info(f"MFA required: IP={ip}, email={email}, risk={risk_score}")

        return recommendations


# Factory function para crear analyzer con perfil específico
SECURITY_PROFILES = {
    'strict': {
        'ip_rate_limit': {'minutes': 5, 'max_failures': 3},
        'email_rate_limit': {'minutes': 10, 'max_failures': 5},
        'risk_thresholds': {'captcha': 30, 'mfa': 50, 'email_verification': 60, 'block': 70}
    },
    'moderate': {
        'ip_rate_limit': {'minutes': 10, 'max_failures': 5},
        'email_rate_limit': {'minutes': 15, 'max_failures': 8},
        'risk_thresholds': {'captcha': 40, 'mfa': 60, 'email_verification': 70, 'block': 90}
    },
    'lenient': {
        'ip_rate_limit': {'minutes': 15, 'max_failures': 10},
        'email_rate_limit': {'minutes': 30, 'max_failures': 15},
        'risk_thresholds': {'captcha': 60, 'mfa': 80, 'email_verification': 85, 'block': 95}
    }
}


def create_security_analyzer(session: AsyncSession, profile: str = 'moderate') -> AuthSecurityAnalyzer:
    """
    Crea un analizador de seguridad con perfil específico.

    Args:
        session: Sesión de SQLAlchemy
        profile: Perfil de seguridad ('strict', 'moderate', 'lenient')

    Returns:
        AuthSecurityAnalyzer configurado
    """
    analyzer = AuthSecurityAnalyzer(session)

    if profile in SECURITY_PROFILES:
        analyzer.config.update(SECURITY_PROFILES[profile])

    return analyzer
