"""Event emitter for graph update events."""

from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from app.rule_engine.models import UpdateEvent


class GraphEventEmitter:
    """Event emitter for broadcasting graph update events to listeners.

    Listeners can subscribe to receive UpdateEvent notifications when
    graph entities are created, updated, or deleted.
    """

    def __init__(self) -> None:
        """Initialize an empty list of listeners."""
        self._listeners: List[Callable[["UpdateEvent"], None]] = []

    def subscribe(self, listener: Callable[["UpdateEvent"], None]) -> None:
        """Subscribe a listener to graph events.

        Args:
            listener: A callable that accepts an UpdateEvent parameter.
                     Will be called whenever an event is emitted.

        Raises:
            ValueError: If the listener is already subscribed.
        """
        if listener in self._listeners:
            raise ValueError("Listener is already subscribed")
        self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[["UpdateEvent"], None]) -> None:
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

    def emit(self, event: "UpdateEvent") -> None:
        """Emit a graph event to all subscribed listeners.

        Args:
            event: The UpdateEvent to broadcast to all listeners.
        """
        for listener in self._listeners:
            listener(event)
