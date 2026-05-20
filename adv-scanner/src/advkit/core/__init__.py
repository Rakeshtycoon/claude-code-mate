"""Core primitives: memory-mapped IO and logging."""
from advkit.core.binreader import BinaryReader, Region, open_reader
from advkit.core.log import configure, get_logger

__all__ = ["BinaryReader", "Region", "open_reader", "configure", "get_logger"]
