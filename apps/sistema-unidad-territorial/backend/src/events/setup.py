"""
Configuración e inicialización del sistema de eventos y observadores.
"""

from src.events.dispatcher import dispatcher
from src.events.observers.notification_observer import notification_observer
from src.core.logging import get_logger


logger = get_logger(__name__)


def setup_event_observers() -> None:
    """
    Registrar todos los observadores del sistema.
    
    Esta función debe ser llamada al iniciar la aplicación para que el
    sistema de notificaciones funcione correctamente.
    """
    logger.info("🔧 Configurando observadores de eventos...")

    # Registrar el observador de notificaciones
    dispatcher.subscribe(notification_observer)

    # Aquí puedes agregar más observadores en el futuro:
    # dispatcher.subscribe(analytics_observer)
    # dispatcher.subscribe(audit_observer)
    # dispatcher.subscribe(otro_observador)

    logger.info("✅ Observadores registrados exitosamente")
    logger.info(f"   📊 Total de tipos de eventos con observadores: {len(dispatcher._observers)}")

    for event_type, observers in dispatcher._observers.items():
        logger.info(f"   • {event_type}: {len(observers)} observador(es)")


def teardown_event_observers() -> None:
    """
    Limpiar todos los observadores (útil para testing o shutdown graceful).
    """
    logger.info("🧹 Limpiando observadores de eventos...")
    dispatcher.clear_all()
    logger.info("✅ Observadores limpiados")
