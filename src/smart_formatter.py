"""
WhisperFlow Desktop - Smart Formatter
Formatage intelligent du texte transcrit via modèle IA léger

Fonctionnalités:
- Ponctuation automatique
- Capitalisation des phrases
- Correction grammaticale légère
- Formatage des listes et nombres
"""

from __future__ import annotations

import re
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

sys.path.append('..')
from config import app_config

# Import lazy de transformers pour éviter de charger ~300MB RAM au démarrage
# La variable sera initialisée lors du premier appel à is_available ou load_model
_HAS_TRANSFORMER: bool | None = None  # None = pas encore vérifié


def _check_transformer_available() -> bool:
    """Vérifie si transformers est disponible (lazy check)"""
    global _HAS_TRANSFORMER
    if _HAS_TRANSFORMER is None:
        try:
            import transformers  # noqa: F401
            _HAS_TRANSFORMER = True
        except ImportError:
            _HAS_TRANSFORMER = False
    return _HAS_TRANSFORMER


class FormattingLevel(Enum):
    """Niveaux de formatage"""
    NONE = "none"           # Pas de formatage
    BASIC = "basic"         # Capitalisation + ponctuation basique
    SMART = "smart"         # IA légère pour ponctuation intelligente
    FULL = "full"           # Correction grammaticale complète


@dataclass(slots=True)
class FormattingResult:
    """Résultat du formatage"""
    original_text: str
    formatted_text: str
    corrections_made: int
    level_used: FormattingLevel


class SmartFormatter:
    """
    Service de formatage intelligent du texte.
    
    Utilise un modèle IA léger pour:
    - Ajouter la ponctuation manquante
    - Corriger la capitalisation
    - Améliorer la lisibilité
    
    Fonctionne en mode dégradé (règles basiques) si le modèle n'est pas dispo.
    """
    
    # Modèle léger pour la ponctuation/capitalisation (~300MB)
    DEFAULT_MODEL = "oliverguhr/fullstop-punctuation-multilang-large"
    
    # Patterns de règles basiques
    SENTENCE_END_PATTERN = re.compile(r'([.!?])\s*')
    MULTIPLE_SPACES = re.compile(r'\s+')
    
    # Mots qui commencent une phrase (français)
    SENTENCE_STARTERS_FR = {
        'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles',
        'le', 'la', 'les', 'un', 'une', 'des', 'ce', 'cette', 'ces',
        'mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses',
        'notre', 'votre', 'leur', 'nos', 'vos', 'leurs',
        'mais', 'ou', 'et', 'donc', 'or', 'ni', 'car',
        'si', 'quand', 'comme', 'parce', 'puisque', 'lorsque',
        'pour', 'dans', 'avec', 'sans', 'sous', 'sur',
    }
    
    def __init__(
        self,
        level: FormattingLevel = FormattingLevel.SMART,
        model_id: str | None = None
    ):
        self.level = level
        self.model_id = model_id or self.DEFAULT_MODEL
        
        # Composants du modèle
        self._pipe = None
        self._is_loaded = False
        self._is_loading = False
        self._load_lock = threading.Lock()
        
        # Callbacks
        self._on_progress: Callable[[str, float], None] | None = None
    
    @property
    def is_loaded(self) -> bool:
        """Retourne True si le modèle est chargé"""
        return self._is_loaded
    
    @property
    def is_available(self) -> bool:
        """Retourne True si le formatage IA est disponible"""
        return _check_transformer_available()
    
    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Définit le callback de progression"""
        self._on_progress = callback
    
    def _report_progress(self, message: str, progress: float):
        """Rapporte la progression"""
        if self._on_progress:
            self._on_progress(message, progress)
    
    def load_model(self) -> bool:
        """
        Charge le modèle de ponctuation.
        Retourne True si chargé avec succès.
        """
        if not _check_transformer_available():
            print("⚠️ Transformers non disponible, formatage basique uniquement")
            return False
        
        with self._load_lock:
            if self._is_loaded:
                return True
            if self._is_loading:
                return False
            self._is_loading = True
        
        try:
            self._report_progress("Chargement du modèle de formatage...", 0.2)
            
            # Import lazy de pipeline ici pour éviter le chargement au démarrage
            from transformers import pipeline
            
            # Utilise le même cache que Whisper
            cache_dir = str(app_config.MODELS_DIR)
            
            # Pipeline de ponctuation/capitalisation
            # Utilise CPU pour ne pas surcharger le GPU avec Whisper
            self._pipe = pipeline(
                "token-classification",
                model=self.model_id,
                aggregation_strategy="simple",
                device="cpu",  # CPU pour ne pas concurrencer Whisper
                model_kwargs={"cache_dir": cache_dir}
            )
            
            self._is_loaded = True
            self._report_progress("Modèle de formatage chargé", 1.0)
            print(f"✨ Modèle de formatage chargé: {self.model_id}")
            return True
            
        except Exception as e:
            print(f"⚠️ Erreur chargement modèle formatage: {e}")
            print("   Utilisation du formatage basique")
            return False
        finally:
            self._is_loading = False
    
    def format(self, text: str) -> FormattingResult:
        """
        Formate le texte selon le niveau configuré.
        
        Args:
            text: Texte brut à formater
            
        Returns:
            FormattingResult avec le texte formaté
        """
        if not text or not text.strip():
            return FormattingResult(
                original_text=text,
                formatted_text=text,
                corrections_made=0,
                level_used=FormattingLevel.NONE
            )
        
        original = text.strip()
        
        # Sélection du niveau de formatage
        if self.level == FormattingLevel.NONE:
            return FormattingResult(
                original_text=original,
                formatted_text=original,
                corrections_made=0,
                level_used=FormattingLevel.NONE
            )
        
        elif self.level == FormattingLevel.BASIC:
            formatted, corrections = self._format_basic(original)
            return FormattingResult(
                original_text=original,
                formatted_text=formatted,
                corrections_made=corrections,
                level_used=FormattingLevel.BASIC
            )
        
        elif self.level in (FormattingLevel.SMART, FormattingLevel.FULL):
            # Essaie le formatage IA, sinon fallback sur basique
            if self._is_loaded and self._pipe:
                formatted, corrections = self._format_smart(original)
                return FormattingResult(
                    original_text=original,
                    formatted_text=formatted,
                    corrections_made=corrections,
                    level_used=FormattingLevel.SMART
                )
            else:
                formatted, corrections = self._format_basic(original)
                return FormattingResult(
                    original_text=original,
                    formatted_text=formatted,
                    corrections_made=corrections,
                    level_used=FormattingLevel.BASIC
                )
        
        return FormattingResult(
            original_text=original,
            formatted_text=original,
            corrections_made=0,
            level_used=FormattingLevel.NONE
        )
    
    def _format_basic(self, text: str) -> tuple[str, int]:
        """
        Formatage basique par règles.
        
        Returns:
            (texte formaté, nombre de corrections)
        """
        corrections = 0
        result = text
        
        # Normalise les espaces multiples
        new_result = self.MULTIPLE_SPACES.sub(' ', result)
        if new_result != result:
            corrections += 1
            result = new_result
        
        # Capitalise la première lettre
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
            corrections += 1
        
        # Capitalise après ponctuation de fin
        def capitalize_after_punct(match):
            nonlocal corrections
            punct = match.group(1)
            rest = match.group(0)[len(punct):].lstrip()
            if rest and rest[0].islower():
                corrections += 1
                return punct + ' ' + rest[0].upper() + rest[1:]
            return punct + ' ' + rest
        
        result = self.SENTENCE_END_PATTERN.sub(capitalize_after_punct, result)
        
        # Ajoute un point final si absent
        if result and result[-1] not in '.!?':
            result += '.'
            corrections += 1
        
        return result, corrections
    
    def _format_smart(self, text: str) -> tuple[str, int]:
        """
        Formatage intelligent via modèle IA.
        
        Le modèle prédit où placer la ponctuation et la capitalisation.
        """
        try:
            # Le modèle de ponctuation attend du texte en minuscules sans ponctuation
            clean_text = text.lower()
            clean_text = re.sub(r'[.!?,;:]', '', clean_text)
            clean_text = self.MULTIPLE_SPACES.sub(' ', clean_text).strip()
            
            if not clean_text:
                return text, 0
            
            # Prédiction
            predictions = self._pipe(clean_text)
            
            # Reconstruit le texte avec ponctuation
            result = self._apply_punctuation_predictions(clean_text, predictions)
            
            # Compte les corrections
            corrections = sum(1 for a, b in zip(text.lower(), result.lower()) if a != b)
            corrections += abs(len(text) - len(result))
            
            return result, corrections
            
        except Exception as e:
            print(f"⚠️ Erreur formatage IA: {e}, fallback basique")
            return self._format_basic(text)
    
    def _apply_punctuation_predictions(
        self, 
        text: str, 
        predictions: list[dict]
    ) -> str:
        """
        Applique les prédictions de ponctuation au texte.
        """
        # Les prédictions contiennent des labels comme:
        # "0" = pas de ponctuation
        # "." = point
        # "," = virgule
        # "?" = question
        # "-" = capitalisation (début de phrase)
        
        words = text.split()
        result_words = []
        capitalize_next = True
        
        for i, word in enumerate(words):
            # Trouve la prédiction pour ce mot
            pred_label = "0"
            for pred in predictions:
                if pred.get('word', '').strip().lower() == word.lower():
                    pred_label = pred.get('entity_group', '0')
                    break
            
            # Capitalise si nécessaire
            if capitalize_next and word:
                word = word[0].upper() + word[1:]
                capitalize_next = False
            
            # Ajoute la ponctuation
            if pred_label in ('.', '?', '!'):
                word += pred_label
                capitalize_next = True
            elif pred_label == ',':
                word += ','
            
            result_words.append(word)
        
        result = ' '.join(result_words)
        
        # Assure une ponctuation finale
        if result and result[-1] not in '.!?':
            result += '.'
        
        return result
    
    def unload_model(self):
        """Décharge le modèle pour libérer la mémoire"""
        with self._load_lock:
            self._pipe = None
            self._is_loaded = False
        
        # Force le garbage collector
        import gc
        gc.collect()
        
        print("🧹 Modèle de formatage déchargé")


class RuleBasedFormatter:
    """
    Formateur basé uniquement sur des règles (sans IA).
    Plus léger et rapide, pour les cas où l'IA n'est pas nécessaire.
    """
    
    # Patterns de correction
    PATTERNS = [
        # Espaces avant ponctuation (français)
        (re.compile(r'\s+([.,;:!?])'), r'\1'),
        # Espace après ponctuation (sauf avant fermeture)
        (re.compile(r'([.,;:!?])(?=[^\s\d\)\]])'), r'\1 '),
        # Espaces multiples
        (re.compile(r'\s{2,}'), ' '),
        # Guillemets français
        (re.compile(r'"([^"]*)"'), r'« \1 »'),
    ]
    
    # Mots à capitaliser
    PROPER_NOUNS = {
        'france', 'paris', 'europe', 'google', 'apple', 'microsoft',
        'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche',
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
    }
    
    @classmethod
    def format(cls, text: str) -> str:
        """Applique les règles de formatage"""
        if not text:
            return text
        
        result = text.strip()
        
        # Applique les patterns
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        
        # Capitalise la première lettre
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        
        # Capitalise après .!?
        result = re.sub(
            r'([.!?])\s+([a-zàâäéèêëïîôùûüç])',
            lambda m: m.group(1) + ' ' + m.group(2).upper(),
            result
        )
        
        # Ponctuation finale
        if result and result[-1] not in '.!?':
            # Détecte les questions
            if any(q in result.lower() for q in 
                   ['est-ce que', 'qu\'est-ce', 'pourquoi', 'comment', 
                    'quand', 'où', 'qui', 'quel', 'combien']):
                result += ' ?'
            else:
                result += '.'
        
        return result


# Instance globale du formateur
_formatter: SmartFormatter | None = None


def get_formatter() -> SmartFormatter:
    """Retourne l'instance globale du formateur"""
    global _formatter
    if _formatter is None:
        _formatter = SmartFormatter(level=FormattingLevel.BASIC)
    return _formatter


def format_text(text: str, level: FormattingLevel = FormattingLevel.BASIC) -> str:
    """
    Fonction utilitaire pour formater du texte rapidement.
    
    Args:
        text: Texte à formater
        level: Niveau de formatage
        
    Returns:
        Texte formaté
    """
    if level == FormattingLevel.NONE:
        return text
    elif level == FormattingLevel.BASIC:
        return RuleBasedFormatter.format(text)
    else:
        formatter = get_formatter()
        formatter.level = level
        result = formatter.format(text)
        return result.formatted_text


# Test standalone
if __name__ == "__main__":
    print("✨ Test du Smart Formatter")
    print("-" * 40)
    
    test_texts = [
        "bonjour comment allez vous",
        "je suis content de vous voir aujourd'hui",
        "est-ce que tu peux m'aider avec ce problème",
        "il fait beau dehors n'est-ce pas",
    ]
    
    print("\n📝 Formatage basique (règles):")
    for text in test_texts:
        formatted = format_text(text, FormattingLevel.BASIC)
        print(f"  '{text}'")
        print(f"  → '{formatted}'")
        print()
    
    print("\n✨ Formatage smart (IA si disponible):")
    formatter = SmartFormatter(level=FormattingLevel.SMART)
    
    if formatter.is_available:
        print("   Chargement du modèle...")
        if formatter.load_model():
            for text in test_texts:
                result = formatter.format(text)
                print(f"  '{text}'")
                print(f"  → '{result.formatted_text}' ({result.corrections_made} corrections)")
                print()
        else:
            print("   ⚠️ Impossible de charger le modèle")
    else:
        print("   ⚠️ Transformers non installé, formatage IA indisponible")
