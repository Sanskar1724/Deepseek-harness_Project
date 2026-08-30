"""Phase 6: risk engine converts probability to score to level."""
from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.services.risk_engine import (
    LEVEL_CRITICAL,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MODERATE,
    classify,
    score_from_proba,
)


def test_score_from_proba_clamps_and_rounds():
    assert score_from_proba(0.0) == 0
    assert score_from_proba(1.0) == 100
    assert score_from_proba(0.876) == 88
    assert score_from_proba(-0.5) == 0
    assert score_from_proba(1.7) == 100


def test_classify_default_thresholds():
    t = get_settings().risk_thresholds()
    assert classify(0) == LEVEL_LOW
    assert classify(t["low"] - 1) == LEVEL_LOW
    assert classify(t["low"]) == LEVEL_MODERATE
    assert classify(t["moderate"] - 1) == LEVEL_MODERATE
    assert classify(t["moderate"]) == LEVEL_HIGH
    assert classify(t["high"] - 1) == LEVEL_HIGH
    assert classify(t["high"]) == LEVEL_CRITICAL
    assert classify(100) == LEVEL_CRITICAL


def test_classify_respects_explicit_thresholds():
    t = {"low": 25, "moderate": 50, "high": 75}
    assert classify(24, thresholds=t) == LEVEL_LOW
    assert classify(25, thresholds=t) == LEVEL_MODERATE
    assert classify(49, thresholds=t) == LEVEL_MODERATE
    assert classify(50, thresholds=t) == LEVEL_HIGH
    assert classify(74, thresholds=t) == LEVEL_HIGH
    assert classify(75, thresholds=t) == LEVEL_CRITICAL


def test_threshold_validation_in_settings():
    with pytest.raises(Exception):
        Settings(risk_threshold_low=-1, risk_threshold_moderate=60, risk_threshold_high=80)
    with pytest.raises(Exception):
        Settings(risk_threshold_low=70, risk_threshold_moderate=60, risk_threshold_high=80)
