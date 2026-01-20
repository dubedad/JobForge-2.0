"""Tests for SSE event models."""

import json
from datetime import datetime

import pytest

from jobforge.demo.events import DemoEvent, EventType


class TestEventType:
    """Tests for EventType enum."""

    def test_has_start_event(self) -> None:
        """START event type should exist."""
        assert EventType.START.value == "start"

    def test_has_table_event(self) -> None:
        """TABLE event type should exist."""
        assert EventType.TABLE.value == "table"

    def test_has_relationship_event(self) -> None:
        """RELATIONSHIP event type should exist."""
        assert EventType.RELATIONSHIP.value == "relationship"

    def test_has_measure_event(self) -> None:
        """MEASURE event type should exist."""
        assert EventType.MEASURE.value == "measure"

    def test_has_complete_event(self) -> None:
        """COMPLETE event type should exist."""
        assert EventType.COMPLETE.value == "complete"

    def test_has_error_event(self) -> None:
        """ERROR event type should exist."""
        assert EventType.ERROR.value == "error"

    def test_has_heartbeat_event(self) -> None:
        """HEARTBEAT event type should exist."""
        assert EventType.HEARTBEAT.value == "heartbeat"

    def test_all_event_types_count(self) -> None:
        """Should have exactly 7 event types."""
        assert len(EventType) == 7


class TestDemoEvent:
    """Tests for DemoEvent dataclass."""

    def test_create_with_event_type_and_data(self) -> None:
        """Should create event with event_type and data."""
        event = DemoEvent(
            event_type=EventType.START,
            data={"total_tables": 24},
        )
        assert event.event_type == EventType.START
        assert event.data == {"total_tables": 24}

    def test_timestamp_defaults_to_now(self) -> None:
        """Timestamp should default to approximately now."""
        before = datetime.now()
        event = DemoEvent(event_type=EventType.TABLE, data={})
        after = datetime.now()

        assert before <= event.timestamp <= after

    def test_custom_timestamp(self) -> None:
        """Should accept custom timestamp."""
        custom_time = datetime(2026, 1, 20, 12, 0, 0)
        event = DemoEvent(
            event_type=EventType.TABLE,
            data={},
            timestamp=custom_time,
        )
        assert event.timestamp == custom_time

    def test_to_sse_dict_returns_correct_format(self) -> None:
        """to_sse_dict should return SSE-compatible dictionary."""
        event = DemoEvent(
            event_type=EventType.TABLE,
            data={"name": "dim_noc", "columns": 9},
        )
        sse = event.to_sse_dict()

        assert "event" in sse
        assert "data" in sse
        assert sse["event"] == "table"

    def test_to_sse_dict_data_is_json_string(self) -> None:
        """SSE data should be JSON-serialized string."""
        event = DemoEvent(
            event_type=EventType.TABLE,
            data={"name": "dim_noc", "columns": 9},
        )
        sse = event.to_sse_dict()

        # Should be a string
        assert isinstance(sse["data"], str)

        # Should be valid JSON
        parsed = json.loads(sse["data"])
        assert parsed["name"] == "dim_noc"
        assert parsed["columns"] == 9

    def test_to_sse_dict_start_event(self) -> None:
        """START event should serialize correctly."""
        event = DemoEvent(
            event_type=EventType.START,
            data={"total_tables": 24, "total_relationships": 23},
        )
        sse = event.to_sse_dict()

        assert sse["event"] == "start"
        parsed = json.loads(sse["data"])
        assert parsed["total_tables"] == 24
        assert parsed["total_relationships"] == 23

    def test_to_sse_dict_complete_event(self) -> None:
        """COMPLETE event should serialize correctly."""
        event = DemoEvent(
            event_type=EventType.COMPLETE,
            data={"success": True, "duration_ms": 1500},
        )
        sse = event.to_sse_dict()

        assert sse["event"] == "complete"
        parsed = json.loads(sse["data"])
        assert parsed["success"] is True
        assert parsed["duration_ms"] == 1500

    def test_to_sse_dict_error_event(self) -> None:
        """ERROR event should serialize correctly."""
        event = DemoEvent(
            event_type=EventType.ERROR,
            data={"message": "Schema not found", "error_type": "FileNotFoundError"},
        )
        sse = event.to_sse_dict()

        assert sse["event"] == "error"
        parsed = json.loads(sse["data"])
        assert parsed["message"] == "Schema not found"
        assert parsed["error_type"] == "FileNotFoundError"

    def test_to_sse_dict_handles_empty_data(self) -> None:
        """Should handle empty data dictionary."""
        event = DemoEvent(event_type=EventType.HEARTBEAT, data={})
        sse = event.to_sse_dict()

        assert sse["event"] == "heartbeat"
        assert sse["data"] == "{}"

    def test_to_sse_dict_handles_nested_data(self) -> None:
        """Should handle nested data structures."""
        event = DemoEvent(
            event_type=EventType.TABLE,
            data={
                "name": "dim_noc",
                "columns": ["id", "name", "code"],
                "metadata": {"source": "StatCan", "version": "2021"},
            },
        )
        sse = event.to_sse_dict()

        parsed = json.loads(sse["data"])
        assert parsed["columns"] == ["id", "name", "code"]
        assert parsed["metadata"]["source"] == "StatCan"
