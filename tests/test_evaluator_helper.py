"""
tests/test_evaluator_helper.py

Tests for the synthetic ground-truth helper that automatically derives
exact character start/end offsets from (entity_text, category) pairs,
and tests for exact entity matching logic.
"""

import pytest
from src.evaluator_helper import resolve_entity_spans
from src.evaluator import run_synthetic_evaluation


class TestGroundTruthHelper:

    def test_single_entity_offset(self):
        sentence = "The CEO Rajesh Kumar will present the financials."
        entities = [("Rajesh Kumar", "PERSON")]
        spans = resolve_entity_spans(sentence, entities)
        assert spans == [(8, 20, "PERSON")]
        assert sentence[spans[0][0]:spans[0][1]] == "Rajesh Kumar"

    def test_multiple_entities_offsets(self):
        sentence = "Sunita Sharma and Vikram Nair are the co-founders."
        entities = [("Sunita Sharma", "PERSON"), ("Vikram Nair", "PERSON")]
        spans = resolve_entity_spans(sentence, entities)
        assert spans == [(0, 13, "PERSON"), (18, 29, "PERSON")]
        assert sentence[spans[0][0]:spans[0][1]] == "Sunita Sharma"
        assert sentence[spans[1][0]:spans[1][1]] == "Vikram Nair"

    def test_repeated_text_sequential_matching(self):
        sentence = "Contact support@example.com or support@example.com for help."
        entities = [("support@example.com", "EMAIL"), ("support@example.com", "EMAIL")]
        spans = resolve_entity_spans(sentence, entities)
        assert len(spans) == 2
        assert spans[0] != spans[1]
        assert sentence[spans[0][0]:spans[0][1]] == "support@example.com"
        assert sentence[spans[1][0]:spans[1][1]] == "support@example.com"

    def test_missing_entity_raises_value_error(self):
        sentence = "This is a simple sentence."
        with pytest.raises(ValueError, match="not found in sentence"):
            resolve_entity_spans(sentence, [("NonExistent", "PERSON")])

    def test_empty_entities(self):
        sentence = "No PII here."
        spans = resolve_entity_spans(sentence, [])
        assert spans == []


class TestExactEntityMatching:

    def test_exact_entity_evaluation_runs_and_produces_metrics(self):
        report = run_synthetic_evaluation(min_score=0.5)
        # Sentence level checks
        assert report.total_sentences == 87
        assert report.positive_sentences == 69
        assert report.negative_sentences == 18
        assert report.sentence_classification.accuracy > 0.95
        assert report.sentence_classification.tp + report.sentence_classification.tn + report.sentence_classification.fp + report.sentence_classification.fn == 87

        # Entity level checks
        assert report.total_target_entities == 74
        assert report.entity_overall.tp > 50
        assert report.entity_overall.precision > 0.6
        assert report.entity_overall.recall > 0.7
