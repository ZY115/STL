"""Deterministic controlled-language registry parser for Stage II sanity checks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


def normalize_controlled_language(text: str) -> str:
    return " ".join(str(text).strip().casefold().split())


class ControlledGrammarParser:
    """Parse only the declared controlled-language registry without repair.

    This baseline intentionally performs exact normalized lookup over the three
    reviewed/draft wordings in each benchmark record.  It is an engineering
    sanity baseline, not a learned translator and not an open-language method.
    """

    def __init__(self, specifications: Sequence[Mapping[str, Any]]) -> None:
        self._registry: Dict[str, Dict[str, Any]] = {}
        for spec in specifications:
            language_items = [spec["canonical_natural_language"], *spec["paraphrases"]]
            for language in language_items:
                key = normalize_controlled_language(str(language))
                if key in self._registry:
                    raise ValueError("controlled-language registry contains a duplicate")
                self._registry[key] = dict(spec["typed_ast"])

    def parse(self, language: str) -> Dict[str, Any]:
        key = normalize_controlled_language(language)
        if key not in self._registry:
            raise ValueError("input is outside the frozen controlled-language registry")
        return dict(self._registry[key])


__all__ = ["ControlledGrammarParser", "normalize_controlled_language"]
