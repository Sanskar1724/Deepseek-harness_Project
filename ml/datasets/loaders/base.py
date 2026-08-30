"""Interface a real-data loader must satisfy.

Keep this tiny so it is easy to add a new source.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DatasetLoader(ABC):
    name: str = "abstract"

    @abstractmethod
    def load(self) -> pd.DataFrame: ...
