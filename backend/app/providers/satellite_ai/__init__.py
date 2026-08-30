"""Satellite AI package - re-export interface + mock."""
from .interface import SatelliteEvidence
from .mock import MockSatelliteAIProvider

__all__ = ["SatelliteEvidence", "MockSatelliteAIProvider"]
