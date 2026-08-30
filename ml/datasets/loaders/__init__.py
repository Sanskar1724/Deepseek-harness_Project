"""Real-data loaders.

When real data is dropped into data/raw/, add a loader here that returns a
pandas DataFrame. The training script in ml/scripts/train_model.py picks
the loader by name.

Available loaders:
  - NasaCoolrLoader: NASA COOLR landslide catalog (CSV)

To add a new loader:
  1. Subclass DatasetLoader
  2. Implement load() -> pd.DataFrame
  3. Add to the LOADER_REGISTRY below
  4. Use via: python -m ml.scripts.train_model --loader nasa_coolr
"""
from ml.datasets.loaders.base import DatasetLoader
from ml.datasets.loaders.nasa_coolr import NasaCoolrLoader

# Registry of available loaders by name
LOADER_REGISTRY = {
    "nasa_coolr": NasaCoolrLoader,
}


def get_loader(name: str, **kwargs) -> DatasetLoader:
    """Get a loader instance by name."""
    if name not in LOADER_REGISTRY:
        available = ", ".join(LOADER_REGISTRY.keys())
        raise ValueError(f"Unknown loader: {name}. Available: {available}")
    return LOADER_REGISTRY[name](**kwargs)


__all__ = ["DatasetLoader", "NasaCoolrLoader", "LOADER_REGISTRY", "get_loader"]
