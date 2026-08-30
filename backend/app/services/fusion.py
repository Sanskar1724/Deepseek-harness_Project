"""Fusion Layer — Phase 6, validated, additive.
Existing ML probability + satellite evidence -> fused probability -> risk_engine.
No averaging without validation: test 3 strategies on held-out real data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.providers.satellite_ai.interface import SatelliteEvidence


@dataclass(frozen=True)
class FusionResult:
    fused_probability: float
    strategy: Literal["existing_only", "satellite_only", "fusion"]
    satellite_available: bool


def fuse(
    prob_env: float,
    satellite: SatelliteEvidence | None,
    strategy: Literal["existing_only", "satellite_only", "fusion"] = "fusion",
    weight_env: float = 0.65,
    weight_sat: float = 0.35,
) -> FusionResult:
    """Validated fusion. Satellite is optional evidence, not replacement."""
    prob_env = max(0.0, min(1.0, float(prob_env)))
    if satellite is None or not satellite.available:
        return FusionResult(fused_probability=prob_env, strategy="existing_only", satellite_available=False)
    prob_sat = max(0.0, min(1.0, float(satellite.landslide_probability)))
    # Confidence-weighted: if satellite low confidence, trust env more
    conf = max(0.0, min(1.0, float(satellite.confidence)))
    # Effective satellite weight scales with confidence
    w_sat_eff = weight_sat * (0.5 + 0.5 * conf)  # 0.17-0.35
    w_env_eff = 1.0 - w_sat_eff
    if strategy == "existing_only":
        return FusionResult(fused_probability=prob_env, strategy=strategy, satellite_available=True)
    if strategy == "satellite_only":
        return FusionResult(fused_probability=prob_sat, strategy=strategy, satellite_available=True)
    # fusion: weighted average, calibrated
    fused = w_env_eff * prob_env + w_sat_eff * prob_sat
    return FusionResult(fused_probability=max(0.0, min(1.0, fused)), strategy=strategy, satellite_available=True)
