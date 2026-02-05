"""Tests pour le module settings (UserSettings)"""

from src.config import OutputMode, WindowMode
from src.utils.settings import UserSettings


class TestUserSettingsFromDict:
    """Tests pour UserSettings.from_dict()"""

    def test_empty_dict_returns_defaults(self):
        settings = UserSettings.from_dict({})
        assert settings.push_to_talk_key == "f2"
        assert settings.output_mode == OutputMode.TYPE
        assert settings.language == "fr"
        assert settings.smart_formatting_enabled is True
        assert settings.smart_formatting_level == "basic"
        assert settings.window_mode == WindowMode.FLOATING
        assert settings.window_position_x == -1
        assert settings.window_position_y == -1

    def test_custom_push_to_talk_key(self):
        settings = UserSettings.from_dict({"push_to_talk_key": "ctrl+f3"})
        assert settings.push_to_talk_key == "ctrl+f3"

    def test_push_to_talk_key_truncated_at_50(self):
        long_key = "a" * 100
        settings = UserSettings.from_dict({"push_to_talk_key": long_key})
        assert len(settings.push_to_talk_key) == 50

    def test_valid_output_mode_type(self):
        settings = UserSettings.from_dict({"output_mode": "type"})
        assert settings.output_mode == OutputMode.TYPE

    def test_valid_output_mode_clipboard(self):
        settings = UserSettings.from_dict({"output_mode": "clipboard"})
        assert settings.output_mode == OutputMode.CLIPBOARD

    def test_invalid_output_mode_defaults(self):
        settings = UserSettings.from_dict({"output_mode": "INVALID"})
        assert settings.output_mode == OutputMode.TYPE

    def test_custom_language(self):
        settings = UserSettings.from_dict({"language": "en"})
        assert settings.language == "en"

    def test_language_truncated_at_10(self):
        settings = UserSettings.from_dict({"language": "a" * 20})
        assert len(settings.language) == 10

    def test_smart_formatting_enabled_true(self):
        settings = UserSettings.from_dict({"smart_formatting_enabled": True})
        assert settings.smart_formatting_enabled is True

    def test_smart_formatting_enabled_false(self):
        settings = UserSettings.from_dict({"smart_formatting_enabled": False})
        assert settings.smart_formatting_enabled is False

    def test_valid_smart_formatting_levels(self):
        for level in ("none", "basic", "smart"):
            settings = UserSettings.from_dict({"smart_formatting_level": level})
            assert settings.smart_formatting_level == level

    def test_invalid_smart_formatting_level_defaults(self):
        settings = UserSettings.from_dict({"smart_formatting_level": "invalid"})
        assert settings.smart_formatting_level == "basic"

    def test_valid_window_mode_floating(self):
        settings = UserSettings.from_dict({"window_mode": "floating"})
        assert settings.window_mode == WindowMode.FLOATING

    def test_valid_window_mode_normal(self):
        settings = UserSettings.from_dict({"window_mode": "normal"})
        assert settings.window_mode == WindowMode.NORMAL

    def test_invalid_window_mode_defaults(self):
        settings = UserSettings.from_dict({"window_mode": "invalid"})
        assert settings.window_mode == WindowMode.FLOATING

    def test_window_position(self):
        settings = UserSettings.from_dict({"window_position_x": 100, "window_position_y": 200})
        assert settings.window_position_x == 100
        assert settings.window_position_y == 200

    def test_unknown_keys_ignored(self):
        settings = UserSettings.from_dict({"unknown_key": "value", "another": 42})
        assert settings.push_to_talk_key == "f2"  # defaults unchanged

    def test_all_fields_set(self):
        data = {
            "push_to_talk_key": "ctrl+space",
            "output_mode": "clipboard",
            "language": "en",
            "smart_formatting_enabled": False,
            "smart_formatting_level": "smart",
            "window_mode": "normal",
            "window_position_x": 50,
            "window_position_y": 75,
        }
        settings = UserSettings.from_dict(data)
        assert settings.push_to_talk_key == "ctrl+space"
        assert settings.output_mode == OutputMode.CLIPBOARD
        assert settings.language == "en"
        assert settings.smart_formatting_enabled is False
        assert settings.smart_formatting_level == "smart"
        assert settings.window_mode == WindowMode.NORMAL
        assert settings.window_position_x == 50
        assert settings.window_position_y == 75


class TestUserSettingsToDict:
    """Tests pour UserSettings.to_dict()"""

    def test_default_to_dict(self):
        settings = UserSettings()
        d = settings.to_dict()
        assert isinstance(d, dict)
        assert d["push_to_talk_key"] == "f2"
        assert d["language"] == "fr"
        assert d["smart_formatting_enabled"] is True

    def test_roundtrip(self):
        original = UserSettings(push_to_talk_key="ctrl+f5", language="en", window_position_x=42)
        d = original.to_dict()
        restored = UserSettings.from_dict(d)
        assert restored.push_to_talk_key == original.push_to_talk_key
        assert restored.language == original.language
        assert restored.window_position_x == original.window_position_x

    def test_to_dict_contains_all_fields(self):
        settings = UserSettings()
        d = settings.to_dict()
        expected_keys = {
            "push_to_talk_key",
            "output_mode",
            "language",
            "smart_formatting_enabled",
            "smart_formatting_level",
            "window_mode",
            "window_position_x",
            "window_position_y",
        }
        assert set(d.keys()) == expected_keys
