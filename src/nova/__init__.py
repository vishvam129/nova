"""Nova: cross-device AI assistant."""

from nova import config as _config
from nova import db as _db

__version__ = "0.1.0"

Config = _config.Config
load_config = _config.load_config
open_store = _db.open_store

__all__ = ["Config", "__version__", "load_config", "open_store"]
