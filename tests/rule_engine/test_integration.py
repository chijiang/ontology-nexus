"""Tests for event emitter and GraphTools integration."""

import pytest
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.models import UpdateEvent


class TestGraphEventEmitter:
    """Tests for GraphEventEmitter class."""

    def test_subscribe_listener(self):
        """Test subscribing a listener."""
        emitter = GraphEventEmitter()
        listener_called = []

        def listener(event: UpdateEvent) -> None:
            listener_called.append(event)

        emitter.subscribe(listener)
        assert listener in emitter._listeners

    def test_subscribe_duplicate_listener_raises_error(self):
        """Test that subscribing a duplicate listener raises an error."""
        emitter = GraphEventEmitter()

        def listener(event: UpdateEvent) -> None:
            pass

        emitter.subscribe(listener)

        with pytest.raises(ValueError, match="already subscribed"):
            emitter.subscribe(listener)

    def test_unsubscribe_listener(self):
        """Test unsubscribing a listener."""
        emitter = GraphEventEmitter()

        def listener(event: UpdateEvent) -> None:
            pass

        emitter.subscribe(listener)
        assert listener in emitter._listeners

        emitter.unsubscribe(listener)
        assert listener not in emitter._listeners

    def test_unsubscribe_nonexistent_listener_raises_error(self):
        """Test that unsubscribing a nonexistent listener raises an error."""
        emitter = GraphEventEmitter()

        def listener(event: UpdateEvent) -> None:
            pass

        with pytest.raises(ValueError, match="not subscribed"):
            emitter.unsubscribe(listener)

    def test_emit_event_to_single_listener(self):
        """Test emitting an event to a single listener."""
        emitter = GraphEventEmitter()
        received_events = []

        def listener(event: UpdateEvent) -> None:
            received_events.append(event)

        emitter.subscribe(listener)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        emitter.emit(test_event)

        assert len(received_events) == 1
        assert received_events[0] is test_event

    def test_emit_event_to_multiple_listeners(self):
        """Test emitting an event to multiple listeners."""
        emitter = GraphEventEmitter()
        listener1_events = []
        listener2_events = []

        def listener1(event: UpdateEvent) -> None:
            listener1_events.append(event)

        def listener2(event: UpdateEvent) -> None:
            listener2_events.append(event)

        emitter.subscribe(listener1)
        emitter.subscribe(listener2)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        emitter.emit(test_event)

        assert len(listener1_events) == 1
        assert len(listener2_events) == 1
        assert listener1_events[0] is test_event
        assert listener2_events[0] is test_event

    def test_emit_multiple_events(self):
        """Test emitting multiple events in sequence."""
        emitter = GraphEventEmitter()
        received_events = []

        def listener(event: UpdateEvent) -> None:
            received_events.append(event)

        emitter.subscribe(listener)

        event1 = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-1",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        event2 = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="po-123",
            property="amount",
            old_value=100,
            new_value=200,
        )

        emitter.emit(event1)
        emitter.emit(event2)

        assert len(received_events) == 2
        assert received_events[0] is event1
        assert received_events[1] is event2

    def test_listener_can_unsubscribe_itself(self):
        """Test that a listener can unsubscribe itself during event handling."""
        emitter = GraphEventEmitter()
        call_count = []

        def listener(event: UpdateEvent) -> None:
            call_count.append(1)
            emitter.unsubscribe(listener)

        emitter.subscribe(listener)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        emitter.emit(test_event)
        assert len(call_count) == 1

        # Listener should no longer receive events
        emitter.emit(test_event)
        assert len(call_count) == 1

    def test_emit_with_no_listeners(self):
        """Test that emitting with no listeners doesn't raise an error."""
        emitter = GraphEventEmitter()

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        # Should not raise any errors
        emitter.emit(test_event)


class TestEventBroadcast:
    """Tests for event broadcasting behavior."""

    def test_event_order_preserved(self):
        """Test that events are broadcast to listeners in subscription order."""
        emitter = GraphEventEmitter()
        results = []

        def listener1(event: UpdateEvent) -> None:
            results.append("listener1")

        def listener2(event: UpdateEvent) -> None:
            results.append("listener2")

        def listener3(event: UpdateEvent) -> None:
            results.append("listener3")

        emitter.subscribe(listener1)
        emitter.subscribe(listener2)
        emitter.subscribe(listener3)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        emitter.emit(test_event)

        assert results == ["listener1", "listener2", "listener3"]

    def test_listener_exception_propagates(self):
        """Test that an exception in a listener propagates to the caller."""
        emitter = GraphEventEmitter()
        listener2_called = []

        def failing_listener(event: UpdateEvent) -> None:
            raise RuntimeError("Listener failed!")

        def working_listener(event: UpdateEvent) -> None:
            listener2_called.append(event)

        # Subscribe working listener first, then failing listener
        emitter.subscribe(working_listener)
        emitter.subscribe(failing_listener)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        # The failing listener should raise an exception
        # Both listeners should have been called before the exception
        with pytest.raises(RuntimeError, match="Listener failed!"):
            emitter.emit(test_event)

        # The working listener was called before the exception
        assert len(listener2_called) == 1

    def test_different_event_types(self):
        """Test that listeners receive different types of events correctly."""
        emitter = GraphEventEmitter()
        received_events = []

        def listener(event: UpdateEvent) -> None:
            received_events.append(event)

        emitter.subscribe(listener)

        events = [
            UpdateEvent(
                entity_type="Supplier",
                entity_id="sup-1",
                property="status",
                old_value="Active",
                new_value="Expired",
            ),
            UpdateEvent(
                entity_type="PurchaseOrder",
                entity_id="po-1",
                property="amount",
                old_value=100,
                new_value=200,
            ),
            UpdateEvent(
                entity_type="Product",
                entity_id="prod-1",
                property="name",
                old_value="Old Name",
                new_value="New Name",
            ),
        ]

        for event in events:
            emitter.emit(event)

        assert len(received_events) == 3
        assert received_events == events

    def test_unsubscribe_mid_broadcast(self):
        """Test unsubscribing a listener while another is being called."""
        emitter = GraphEventEmitter()
        results = []

        def listener1(event: UpdateEvent) -> None:
            results.append("listener1")

        def listener2(event: UpdateEvent) -> None:
            results.append("listener2")

        def listener3(event: UpdateEvent) -> None:
            results.append("listener3")

        emitter.subscribe(listener1)
        emitter.subscribe(listener2)
        emitter.subscribe(listener3)

        test_event = UpdateEvent(
            entity_type="Supplier",
            entity_id="supplier-123",
            property="status",
            old_value="Active",
            new_value="Expired",
        )

        # Remove listener2 before emitting
        emitter.unsubscribe(listener2)
        emitter.emit(test_event)

        assert results == ["listener1", "listener3"]
