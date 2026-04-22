"""Nova: cross-device AI assistant."""

from nova import config as _config

__version__ = "0.1.0"

Config = _config.Config
load_config = _config.load_config

__all__ = ["Config", "__version__", "load_config"]
