"""Event emitter for graph update events."""

from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from app.rule_engine.models import UpdateEvent, GraphViewEvent

EventT = "UpdateEvent | GraphViewEvent"


class GraphEventEmitter:
    """Event emitter for broadcasting graph update events to listeners.

    Listeners can subscribe to receive UpdateEvent notifications when
    graph entities are created, updated, or deleted.
    """

    def __init__(self) -> None:
        """Initialize an empty list of listeners."""
        self._listeners: List[Callable[[EventT], None]] = []

    def subscribe(self, listener: Callable[[EventT], None]) -> None:
        """Subscribe a listener to graph events.

        Args:
            listener: A callable that accepts an event parameter.
                     Will be called whenever an event is emitted.

        Raises:
            ValueError: If the listener is already subscribed.
        """
        if listener in self._listeners:
            raise ValueError("Listener is already subscribed")
        self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[EventT], None]) -> None:
        """Unsubscribe a listener from graph events.

        Args:
            listener: The listener to remove.

        Raises:
            ValueError: If the listener is not subscribed.
        """
        try:
            self._listeners.remove(listener)
        except ValueError:
            raise ValueError("Listener is not subscribed") from None

    def emit(self, event: EventT) -> None:
        """Emit a graph event to all subscribed listeners.

        Args:
            event: The event to broadcast to all listeners.
        """
        import logging

        logger = logging.getLogger(__name__)
        # Handle different event types for logging
        if hasattr(event, "entity_type") and hasattr(event, "property"):
             logger.debug(
                f"EventEmitter.emit() called: {event.entity_type}.{event.property} on {event.entity_id}"
            )
        else:
             logger.debug(f"EventEmitter.emit() called: {type(event).__name__}")
             
        # logger.debug(f"EventEmitter has {len(self._listeners)} listeners")

        for listener in self._listeners:
            # logger.debug(f"Calling listener: {listener}")
            listener(event)
