"""Tests pour le parsing de raccourcis clavier"""

from src.utils.hotkey_listener import parse_hotkey


class TestParseHotkey:
    """Tests pour la fonction parse_hotkey()"""

    def test_single_key(self):
        key, modifiers = parse_hotkey("f2")
        assert key == "f2"
        assert modifiers == frozenset()

    def test_single_key_letter(self):
        key, modifiers = parse_hotkey("a")
        assert key == "a"
        assert modifiers == frozenset()

    def test_ctrl_modifier(self):
        key, modifiers = parse_hotkey("ctrl+f2")
        assert key == "f2"
        assert modifiers == frozenset({"ctrl"})

    def test_alt_modifier(self):
        key, modifiers = parse_hotkey("alt+f2")
        assert key == "f2"
        assert modifiers == frozenset({"alt"})

    def test_shift_modifier(self):
        key, modifiers = parse_hotkey("shift+f2")
        assert key == "f2"
        assert modifiers == frozenset({"shift"})

    def test_multiple_modifiers(self):
        key, modifiers = parse_hotkey("ctrl+shift+f2")
        assert key == "f2"
        assert modifiers == frozenset({"ctrl", "shift"})

    def test_three_modifiers(self):
        key, modifiers = parse_hotkey("ctrl+alt+shift+space")
        assert key == "space"
        assert modifiers == frozenset({"ctrl", "alt", "shift"})

    def test_case_insensitive(self):
        key, modifiers = parse_hotkey("CTRL+F2")
        assert key == "f2"
        assert modifiers == frozenset({"ctrl"})

    def test_mixed_case(self):
        key, modifiers = parse_hotkey("Ctrl+Shift+Space")
        assert key == "space"
        assert modifiers == frozenset({"ctrl", "shift"})

    def test_control_alias(self):
        key, modifiers = parse_hotkey("control+a")
        assert modifiers == frozenset({"ctrl"})

    def test_ctrl_l_alias(self):
        key, modifiers = parse_hotkey("ctrl_l+a")
        assert modifiers == frozenset({"ctrl"})

    def test_ctrl_r_alias(self):
        key, modifiers = parse_hotkey("ctrl_r+a")
        assert modifiers == frozenset({"ctrl"})

    def test_alt_l_alias(self):
        key, modifiers = parse_hotkey("alt_l+x")
        assert modifiers == frozenset({"alt"})

    def test_alt_r_alias(self):
        key, modifiers = parse_hotkey("alt_r+x")
        assert modifiers == frozenset({"alt"})

    def test_shift_l_alias(self):
        key, modifiers = parse_hotkey("shift_l+tab")
        assert modifiers == frozenset({"shift"})

    def test_shift_r_alias(self):
        key, modifiers = parse_hotkey("shift_r+tab")
        assert modifiers == frozenset({"shift"})

    def test_cmd_modifier(self):
        key, modifiers = parse_hotkey("cmd+c")
        assert modifiers == frozenset({"cmd"})

    def test_win_alias(self):
        key, modifiers = parse_hotkey("win+v")
        assert key == "v"
        assert modifiers == frozenset({"cmd"})

    def test_super_alias(self):
        key, modifiers = parse_hotkey("super+l")
        assert modifiers == frozenset({"cmd"})

    def test_meta_alias(self):
        key, modifiers = parse_hotkey("meta+x")
        assert modifiers == frozenset({"cmd"})

    def test_special_character_apostrophe(self):
        key, modifiers = parse_hotkey("ctrl+'")
        assert key == "'"
        assert modifiers == frozenset({"ctrl"})

    def test_escape_key(self):
        key, modifiers = parse_hotkey("escape")
        assert key == "escape"
        assert modifiers == frozenset()

    def test_space_key(self):
        key, modifiers = parse_hotkey("space")
        assert key == "space"
        assert modifiers == frozenset()

    def test_returns_frozenset(self):
        _, modifiers = parse_hotkey("ctrl+a")
        assert isinstance(modifiers, frozenset)
