"""Read API, OGC API - EDR, Zarr over HTTP and standard exports."""

from importlib.metadata import version

__all__ = ["__version__"]

__version__: str = version("shoalscope-api")
