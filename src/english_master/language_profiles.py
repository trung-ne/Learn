"""Canonical target-language profiles and safe language-scoped paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_SUPPORTED_LANGUAGE_CODES = frozenset({"en", "de"})


@dataclass(frozen=True)
class LanguageProfile:
    """The small stable boundary shared by language-scoped course artifacts."""

    language_code: str
    display_name: str

    def relative_path(self, *parts: str) -> Path:
        """Return a validated path below this language's course namespace."""

        for part in parts:
            candidate = Path(part)
            if not part or candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(f"unsafe language-scoped path component: {part!r}")
        return Path("course") / self.language_code / Path(*parts)


_PROFILES = {
    "en": LanguageProfile(language_code="en", display_name="English"),
    "de": LanguageProfile(language_code="de", display_name="German"),
}


def language_profile(language_code: str) -> LanguageProfile:
    """Return one currently supported canonical target-language profile."""

    if not isinstance(language_code, str) or language_code not in _SUPPORTED_LANGUAGE_CODES:
        supported = ", ".join(sorted(_SUPPORTED_LANGUAGE_CODES))
        raise ValueError(f"unsupported language code {language_code!r}; supported codes: {supported}")
    return _PROFILES[language_code]


def course_path(language_code: str, *parts: str) -> Path:
    """Resolve a relative course path without granting access outside its namespace."""

    return language_profile(language_code).relative_path(*parts)


def knowledge_graph_id(language_code: str, tier: str, dimension: str) -> str:
    """Build a future language-qualified knowledge-graph identifier."""

    language_profile(language_code)
    tier_slug = tier.lower().replace(".", "_")
    if not tier_slug or not dimension or not dimension.replace("_", "").isalnum():
        raise ValueError("tier and dimension must be nonempty ASCII identifier components")
    return f"kg_{language_code}_{tier_slug}_{dimension}"


def data_path(language_code: str, area: str, *parts: str) -> Path:
    """Resolve a safe language-scoped data path for a declared core area."""

    if area not in {"taxonomy", "learner-state", "knowledge-graph"}:
        raise ValueError(f"unsupported language-scoped data area {area!r}")
    for part in parts:
        candidate = Path(part)
        if not part or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"unsafe language-scoped path component: {part!r}")
    language_profile(language_code)
    return Path("data") / area / language_code / Path(*parts)
