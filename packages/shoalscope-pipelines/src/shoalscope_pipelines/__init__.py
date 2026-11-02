"""Dagster definitions: assets, partitions, sensors, schedules and checks."""

from importlib.metadata import version

__all__ = ["__version__"]

__version__: str = version("shoalscope-pipelines")
