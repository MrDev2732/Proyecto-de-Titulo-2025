"""
Dispatcher de eventos para el sistema de observadores.
"""

from typing import Dict, List
from src.events.base import Event, Observer, EventType
from src.core.logging import get_logger


logger = get_logger(__name__)


class EventDispatcher:
    """
    Dispatcher centralizado de eventos.

    Permite registrar observadores y notificarlos cuando ocurren eventos.
    """

    _instance = None
    _observers: Dict[EventType, List[Observer]] = {}

    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(EventDispatcher, cls).__new__(cls)
            cls._instance._observers = {}
        return cls._instance

    def subscribe(self, observer: Observer) -> None:
        """
        Registrar un observador para los eventos a los que está suscrito.

        Args:
            observer: El observador a registrar
        """
        for event_type in observer.get_subscribed_events():
            if event_type not in self._observers:
                self._observers[event_type] = []

            if observer not in self._observers[event_type]:
                self._observers[event_type].append(observer)
                logger.info(f"📢 Observer {observer.__class__.__name__} registered for event {event_type}")

    def unsubscribe(self, observer: Observer, event_type: EventType) -> None:
        """
        Desregistrar un observador de un tipo de evento específico.

        Args:
            observer: El observador a desregistrar
            event_type: El tipo de evento del que desregistrar
        """
        if event_type in self._observers:
            if observer in self._observers[event_type]:
                self._observers[event_type].remove(observer)
                logger.info(f"🔕 Observer {observer.__class__.__name__} unregistered from event {event_type}")

    async def dispatch(self, event: Event) -> None:
        """
        Despachar un evento a todos los observadores suscritos.

        Args:
            event: El evento a despachar
        """
        logger.info(f"🔔 Dispatching event: {event}")

        if event.event_type in self._observers:
            observers = self._observers[event.event_type]
            logger.info(f"   Found {len(observers)} observer(s) for event {event.event_type}")

            for observer in observers:
                try:
                    await observer.update(event)
                    logger.info(f"   ✅ Observer {observer.__class__.__name__} notified successfully")
                except Exception as e:
                    logger.error(f"   ❌ Error notifying observer {observer.__class__.__name__}: {e}")
        else:
            logger.info(f"   No observers registered for event {event.event_type}")

    def clear_all(self) -> None:
        """Limpiar todos los observadores registrados (útil para testing)."""
        self._observers.clear()
        logger.info("🧹 All observers cleared")

    def get_observers_count(self, event_type: EventType) -> int:
        """
        Obtener el número de observadores para un tipo de evento.

        Args:
            event_type: El tipo de evento

        Returns:
            Número de observadores registrados
        """
        return len(self._observers.get(event_type, []))


# Instancia global del dispatcher
dispatcher = EventDispatcher()
