"""Tests pour le module history"""

from datetime import datetime

import pytest

from src.utils.history import TranscriptionEntry, TranscriptionHistory


class TestTranscriptionEntry:
    """Tests pour TranscriptionEntry"""

    def test_create_sets_fields(self):
        entry = TranscriptionEntry.create(text="Bonjour", duration=1.5, language="fr", processing_time=0.3)
        assert entry.text == "Bonjour"
        assert entry.duration == 1.5
        assert entry.language == "fr"
        assert entry.processing_time == 0.3

    def test_create_sets_timestamp(self):
        entry = TranscriptionEntry.create(text="Test", duration=1.0, language="fr", processing_time=0.1)
        assert entry.timestamp != ""
        # Vérifie que c'est un format ISO valide
        datetime.fromisoformat(entry.timestamp)

    def test_formatted_time_valid_iso(self):
        entry = TranscriptionEntry(
            text="Test",
            timestamp="2024-06-15T14:30:45.123456",
            duration=1.0,
            language="fr",
            processing_time=0.1,
        )
        assert entry.formatted_time == "14:30:45"

    def test_formatted_time_invalid_iso_fallback(self):
        entry = TranscriptionEntry(
            text="Test",
            timestamp="not-a-valid-timestamp",
            duration=1.0,
            language="fr",
            processing_time=0.1,
        )
        # Fallback: premiers 8 caractères
        assert entry.formatted_time == "not-a-va"

    def test_formatted_time_empty_string(self):
        entry = TranscriptionEntry(
            text="Test",
            timestamp="",
            duration=1.0,
            language="fr",
            processing_time=0.1,
        )
        assert entry.formatted_time == ""

    def test_to_dict(self):
        entry = TranscriptionEntry(
            text="Bonjour",
            timestamp="2024-01-01T12:00:00",
            duration=2.0,
            language="fr",
            processing_time=0.5,
        )
        d = entry.to_dict()
        assert d["text"] == "Bonjour"
        assert d["timestamp"] == "2024-01-01T12:00:00"
        assert d["duration"] == 2.0
        assert d["language"] == "fr"
        assert d["processing_time"] == 0.5

    def test_from_dict_complete(self):
        data = {
            "text": "Hello",
            "timestamp": "2024-01-01T10:00:00",
            "duration": 3.0,
            "language": "en",
            "processing_time": 0.8,
        }
        entry = TranscriptionEntry.from_dict(data)
        assert entry.text == "Hello"
        assert entry.timestamp == "2024-01-01T10:00:00"
        assert entry.duration == 3.0
        assert entry.language == "en"
        assert entry.processing_time == 0.8

    def test_from_dict_empty_uses_defaults(self):
        entry = TranscriptionEntry.from_dict({})
        assert entry.text == ""
        assert entry.timestamp == ""
        assert entry.duration == 0.0
        assert entry.language == "fr"
        assert entry.processing_time == 0.0

    def test_from_dict_missing_keys(self):
        entry = TranscriptionEntry.from_dict({"text": "Partial"})
        assert entry.text == "Partial"
        assert entry.duration == 0.0

    def test_roundtrip(self):
        original = TranscriptionEntry(
            text="Roundtrip",
            timestamp="2024-06-01T08:30:00",
            duration=5.0,
            language="en",
            processing_time=1.2,
        )
        restored = TranscriptionEntry.from_dict(original.to_dict())
        assert restored.text == original.text
        assert restored.timestamp == original.timestamp
        assert restored.duration == original.duration
        assert restored.language == original.language
        assert restored.processing_time == original.processing_time


class TestTranscriptionHistory:
    """Tests pour TranscriptionHistory (sans persistance)"""

    def test_empty_history(self):
        history = TranscriptionHistory(persist=False)
        assert len(history) == 0
        assert history.last is None

    def test_add_entry(self):
        history = TranscriptionHistory(persist=False)
        history.add("Bonjour")
        assert len(history) == 1
        assert history.last.text == "Bonjour"

    def test_add_empty_text_ignored(self):
        history = TranscriptionHistory(persist=False)
        history.add("")
        assert len(history) == 0

    def test_add_whitespace_only_ignored(self):
        history = TranscriptionHistory(persist=False)
        history.add("   ")
        assert len(history) == 0

    def test_add_strips_text(self):
        history = TranscriptionHistory(persist=False)
        history.add("  Bonjour  ")
        assert history.last.text == "Bonjour"

    def test_max_size_respected(self):
        history = TranscriptionHistory(max_size=3, persist=False)
        for i in range(5):
            history.add(f"Entry {i}")
        assert len(history) == 3
        # Les plus anciens sont supprimés
        texts = [e.text for e in history.get_all()]
        assert texts == ["Entry 2", "Entry 3", "Entry 4"]

    def test_get_recent(self):
        history = TranscriptionHistory(persist=False)
        for i in range(10):
            history.add(f"Entry {i}")
        recent = history.get_recent(3)
        assert len(recent) == 3
        assert recent[-1].text == "Entry 9"

    def test_get_recent_more_than_available(self):
        history = TranscriptionHistory(persist=False)
        history.add("Only one")
        recent = history.get_recent(10)
        assert len(recent) == 1

    def test_clear(self):
        history = TranscriptionHistory(persist=False)
        history.add("Test")
        history.clear()
        assert len(history) == 0

    def test_total_duration(self):
        history = TranscriptionHistory(persist=False)
        history.add("A", duration=1.5)
        history.add("B", duration=2.5)
        assert history.total_duration == 4.0

    def test_total_processing_time(self):
        history = TranscriptionHistory(persist=False)
        history.add("A", processing_time=0.3)
        history.add("B", processing_time=0.7)
        assert history.total_processing_time == pytest.approx(1.0)

    def test_iteration(self):
        history = TranscriptionHistory(persist=False)
        history.add("A")
        history.add("B")
        texts = [e.text for e in history]
        assert texts == ["A", "B"]

    def test_export_text(self):
        history = TranscriptionHistory(persist=False)
        entry = TranscriptionEntry(
            text="Bonjour",
            timestamp="2024-06-15T14:30:45",
            duration=1.0,
            language="fr",
            processing_time=0.1,
        )
        history.add_entry(entry)
        export = history.export_text()
        assert "[14:30:45] Bonjour" in export
