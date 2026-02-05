"""Tests pour le module transcription_service (fonctions pures)"""

import re

from src.transcription_service import (
    _HALLUCINATION_PATTERN,
    _WHITESPACE_PATTERN,
    TranscriptionService,
)


class TestCleanHallucinations:
    """Tests pour TranscriptionService._clean_hallucinations()"""

    def setup_method(self):
        self.service = TranscriptionService.__new__(TranscriptionService)

    def test_clean_text_unchanged(self):
        assert self.service._clean_hallucinations("Bonjour tout le monde") == "Bonjour tout le monde"

    def test_empty_string(self):
        assert self.service._clean_hallucinations("") == ""

    def test_removes_merci_avoir_regarde(self):
        result = self.service._clean_hallucinations("Bonjour Merci d'avoir regardé")
        assert "Merci d'avoir regardé" not in result
        assert "Bonjour" in result

    def test_removes_sous_titres_realises(self):
        result = self.service._clean_hallucinations("Test Sous-titres réalisés par la communauté")
        assert "Sous-titres réalisés" not in result

    def test_removes_sous_titres_par(self):
        result = self.service._clean_hallucinations("Texte Sous-titres par X")
        assert "Sous-titres par" not in result

    def test_removes_abonnez_vous(self):
        result = self.service._clean_hallucinations("Bonjour Abonnez-vous")
        assert "Abonnez-vous" not in result

    def test_removes_musique_brackets(self):
        result = self.service._clean_hallucinations("[Musique] Bonjour")
        assert "[Musique]" not in result
        assert "Bonjour" in result

    def test_removes_applaudissements(self):
        result = self.service._clean_hallucinations("[Applaudissements] Bravo")
        assert "[Applaudissements]" not in result
        assert "Bravo" in result

    def test_removes_musique_parentheses(self):
        result = self.service._clean_hallucinations("(Musique) Intro")
        assert "(Musique)" not in result

    def test_removes_ellipsis(self):
        result = self.service._clean_hallucinations("test... suite")
        assert "..." not in result

    def test_keeps_two_dots(self):
        # Seulement 3+ points sont supprimés
        result = self.service._clean_hallucinations("test.. suite")
        assert ".." in result

    def test_case_insensitive(self):
        result = self.service._clean_hallucinations("MERCI D'AVOIR REGARDÉ")
        assert result.strip() == ""

    def test_multiple_hallucinations(self):
        text = "[Musique] Merci d'avoir regardé [Applaudissements]"
        result = self.service._clean_hallucinations(text)
        assert result.strip() == ""

    def test_normalizes_whitespace(self):
        result = self.service._clean_hallucinations("Bonjour   tout    le    monde")
        assert "  " not in result
        assert result == "Bonjour tout le monde"

    def test_strips_result(self):
        result = self.service._clean_hallucinations("  Bonjour  ")
        assert result == "Bonjour"

    def test_hallucination_only_returns_empty(self):
        result = self.service._clean_hallucinations("Merci d'avoir regardé")
        assert result == ""

    def test_preserves_normal_merci(self):
        # "Merci de votre aide" ne doit pas être supprimé (pas dans les patterns)
        result = self.service._clean_hallucinations("Merci de votre aide")
        assert "Merci de votre aide" in result


class TestHallucinationPattern:
    """Tests pour le pattern regex compilé"""

    def test_pattern_is_compiled(self):
        assert isinstance(_HALLUCINATION_PATTERN, re.Pattern)

    def test_pattern_is_case_insensitive(self):
        assert _HALLUCINATION_PATTERN.flags & re.IGNORECASE

    def test_whitespace_pattern_is_compiled(self):
        assert isinstance(_WHITESPACE_PATTERN, re.Pattern)

    def test_whitespace_pattern_matches_multiple_spaces(self):
        assert _WHITESPACE_PATTERN.sub(" ", "a  b   c") == "a b c"

    def test_whitespace_pattern_matches_tabs(self):
        assert _WHITESPACE_PATTERN.sub(" ", "a\tb") == "a b"

    def test_whitespace_pattern_matches_newlines(self):
        assert _WHITESPACE_PATTERN.sub(" ", "a\nb") == "a b"
