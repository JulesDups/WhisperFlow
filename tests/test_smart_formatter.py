"""Tests pour le module smart_formatter"""

from src.smart_formatter import (
    FormattingLevel,
    FormattingResult,
    RuleBasedFormatter,
    SmartFormatter,
)


class TestRuleBasedFormatter:
    """Tests pour RuleBasedFormatter.format()"""

    def test_empty_string(self):
        assert RuleBasedFormatter.format("") == ""

    def test_none_returns_none(self):
        assert RuleBasedFormatter.format(None) is None

    def test_capitalize_first_letter(self):
        result = RuleBasedFormatter.format("bonjour")
        assert result[0] == "B"

    def test_already_capitalized(self):
        result = RuleBasedFormatter.format("Bonjour")
        assert result.startswith("Bonjour")

    def test_adds_final_period(self):
        result = RuleBasedFormatter.format("bonjour")
        assert result == "Bonjour."

    def test_keeps_existing_period(self):
        result = RuleBasedFormatter.format("Bonjour.")
        assert result == "Bonjour."

    def test_keeps_exclamation(self):
        result = RuleBasedFormatter.format("Bonjour!")
        assert result == "Bonjour!"

    def test_keeps_question_mark(self):
        result = RuleBasedFormatter.format("Vraiment?")
        assert result == "Vraiment?"

    def test_capitalize_after_period(self):
        result = RuleBasedFormatter.format("bonjour. comment vas tu")
        assert "Comment" in result

    def test_capitalize_after_exclamation(self):
        result = RuleBasedFormatter.format("super! merci")
        assert "Merci" in result

    def test_capitalize_after_question(self):
        result = RuleBasedFormatter.format("vraiment? oui")
        assert "Oui" in result

    def test_detect_french_question_est_ce_que(self):
        result = RuleBasedFormatter.format("est-ce que tu viens")
        assert result.endswith("?")

    def test_detect_french_question_pourquoi(self):
        result = RuleBasedFormatter.format("pourquoi pas")
        assert result.endswith("?")

    def test_detect_french_question_comment(self):
        result = RuleBasedFormatter.format("comment ça va")
        assert result.endswith("?")

    def test_detect_french_question_quand(self):
        result = RuleBasedFormatter.format("quand est-ce qu'on mange")
        assert result.endswith("?")

    def test_detect_french_question_combien(self):
        result = RuleBasedFormatter.format("combien ça coûte")
        assert result.endswith("?")

    def test_spaces_before_punctuation_removed(self):
        result = RuleBasedFormatter.format("bonjour ,monde")
        assert " ," not in result

    def test_space_after_punctuation_added(self):
        result = RuleBasedFormatter.format("bonjour,monde")
        assert ", " in result

    def test_multiple_spaces_normalized(self):
        result = RuleBasedFormatter.format("bonjour   monde")
        assert "   " not in result

    def test_straight_quotes_to_guillemets(self):
        result = RuleBasedFormatter.format('"citation"')
        assert "«" in result
        assert "»" in result

    def test_strips_whitespace(self):
        result = RuleBasedFormatter.format("  bonjour  ")
        assert not result.startswith(" ")
        assert result.startswith("B")

    def test_accented_characters(self):
        result = RuleBasedFormatter.format("écoute. à bientôt")
        # Le é majuscule n'est pas garanti, mais le à après le point devrait être capitalisé
        assert "À" in result


class TestSmartFormatterBasic:
    """Tests pour SmartFormatter._format_basic()"""

    def setup_method(self):
        self.formatter = SmartFormatter(level=FormattingLevel.BASIC)

    def test_returns_tuple(self):
        result = self.formatter._format_basic("bonjour")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_capitalizes_first_letter(self):
        text, corrections = self.formatter._format_basic("bonjour")
        assert text[0] == "B"
        assert corrections >= 1

    def test_already_capitalized_no_extra_capital(self):
        text, corrections = self.formatter._format_basic("Bonjour monde.")
        assert text.startswith("Bonjour")

    def test_adds_final_period(self):
        text, corrections = self.formatter._format_basic("Bonjour")
        assert text == "Bonjour."
        assert corrections >= 1

    def test_normalizes_multiple_spaces(self):
        text, corrections = self.formatter._format_basic("Bonjour   monde.")
        assert "   " not in text
        assert corrections >= 1

    def test_capitalizes_first_letter_only(self):
        # _format_basic capitalise la première lettre
        text, corrections = self.formatter._format_basic("bonjour comment allez vous")
        assert text.startswith("B")
        assert corrections >= 1

    def test_counts_corrections(self):
        # lowercase start + no final period = at least 2 corrections
        _, corrections = self.formatter._format_basic("bonjour")
        assert corrections >= 2


class TestSmartFormatterFormat:
    """Tests pour SmartFormatter.format()"""

    def test_none_level_returns_original(self):
        formatter = SmartFormatter(level=FormattingLevel.NONE)
        result = formatter.format("bonjour")
        assert result.formatted_text == "bonjour"
        assert result.level_used == FormattingLevel.NONE
        assert result.corrections_made == 0

    def test_empty_string(self):
        formatter = SmartFormatter(level=FormattingLevel.BASIC)
        result = formatter.format("")
        assert result.formatted_text == ""
        assert result.corrections_made == 0

    def test_whitespace_only(self):
        formatter = SmartFormatter(level=FormattingLevel.BASIC)
        result = formatter.format("   ")
        assert result.corrections_made == 0

    def test_basic_level(self):
        formatter = SmartFormatter(level=FormattingLevel.BASIC)
        result = formatter.format("bonjour")
        assert isinstance(result, FormattingResult)
        assert result.level_used == FormattingLevel.BASIC
        assert result.formatted_text == "Bonjour."

    def test_smart_level_fallback_to_basic(self):
        # Sans modèle chargé, SMART doit fallback sur BASIC
        formatter = SmartFormatter(level=FormattingLevel.SMART)
        result = formatter.format("bonjour")
        assert result.level_used == FormattingLevel.BASIC

    def test_preserves_original_text(self):
        formatter = SmartFormatter(level=FormattingLevel.BASIC)
        result = formatter.format("bonjour")
        assert result.original_text == "bonjour"

    def test_strips_input(self):
        formatter = SmartFormatter(level=FormattingLevel.BASIC)
        result = formatter.format("  bonjour  ")
        assert result.original_text == "bonjour"
