"""
evaluator_helper.py — Ground-truth offset derivation and validation.

Derives exact character start/end offsets automatically from (entity_text, category)
pairs, guaranteeing that every ground-truth span matches the source sentence text exactly.
"""

from typing import List, Tuple


def resolve_entity_spans(sentence: str, raw_entities: List[Tuple[str, str]]) -> List[Tuple[int, int, str]]:
    """
    Derives exact (start, end, category) character offsets from (entity_text, category) pairs.

    Handles:
    - Multiple entities of different or same types in one sentence.
    - Repeated entity occurrences sequentially from the last matched position.
    - Out-of-order entity listings by falling back to full-sentence search if needed.

    Raises:
        ValueError: If an entity_text cannot be found in the sentence.
    """
    spans: List[Tuple[int, int, str]] = []
    current_search_pos = 0

    for entity_text, category in raw_entities:
        start_idx = sentence.find(entity_text, current_search_pos)
        if start_idx == -1:
            start_idx = sentence.find(entity_text, 0)
        if start_idx == -1:
            raise ValueError(f"Entity '{entity_text}' not found in sentence: '{sentence}'")
        end_idx = start_idx + len(entity_text)
        spans.append((start_idx, end_idx, category))
        current_search_pos = end_idx

    # Sort spans by start index
    spans.sort(key=lambda s: (s[0], s[1]))
    return spans
