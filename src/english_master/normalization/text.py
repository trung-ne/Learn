"""Pure, deterministic text normalization and tokenization."""

from __future__ import annotations

import re
import unicodedata

from english_master.normalization.models import NormalizationPolicy

_WHITESPACE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_display_text(text: str, policy: NormalizationPolicy | None = None) -> str:
    """Normalize storage-safe Unicode, line endings, and whitespace only.

    This preserves case, punctuation, apostrophes, and non-ASCII characters. The
    source text itself remains separately retained by every processed record.
    """

    selected = policy or NormalizationPolicy()
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = unicodedata.normalize(selected.unicode_form, text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if selected.collapse_whitespace:
        normalized = _WHITESPACE.sub(" ", normalized)
    return normalized.strip()


def normalize_comparison_text(text: str, policy: NormalizationPolicy | None = None) -> str:
    """Return a lossy comparison-only representation without altering display text."""

    selected = policy or NormalizationPolicy()
    normalized = normalize_display_text(text, selected)
    if selected.casefold:
        normalized = normalized.casefold()
    if selected.punctuation != "space":
        raise ValueError(f"Unsupported punctuation policy: {selected.punctuation!r}")

    # Apostrophes within a word are retained because they distinguish forms such
    # as "well" and "we'll". Other punctuation becomes a token boundary.
    characters: list[str] = []
    for index, character in enumerate(normalized):
        category = unicodedata.category(character)
        apostrophe_inside_word = (
            character in {"'", "’"}
            and index > 0
            and index + 1 < len(normalized)
            and normalized[index - 1].isalnum()
            and normalized[index + 1].isalnum()
        )
        if category.startswith("P") and not apostrophe_inside_word:
            characters.append(" ")
        else:
            characters.append("'" if character == "’" and apostrophe_inside_word else character)
    return _WHITESPACE.sub(" ", "".join(characters)).strip()


def comparison_characters(text: str) -> str:
    """Remove token-boundary spaces for character n-gram comparison."""

    return "".join(text.split())


def character_ngrams(text: str, size: int) -> frozenset[str]:
    """Return a deterministic set of overlapping character n-grams."""

    if size < 1:
        raise ValueError("ngram size must be positive")
    compact = comparison_characters(text)
    if len(compact) < size:
        return frozenset()
    return frozenset(compact[index : index + size] for index in range(len(compact) - size + 1))
