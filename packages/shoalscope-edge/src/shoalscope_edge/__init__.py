"""Edge service: streaming processing next to the instrument and a budgeted NATS uplink."""

from importlib.metadata import version

__all__ = ["__version__"]

__version__: str = version("shoalscope-edge")
