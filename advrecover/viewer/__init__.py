"""Qt desktop viewer.

Importing this package does not require PySide6/pyvistaqt; those are only
needed when :func:`advrecover.viewer.app.launch` is actually called.
"""
from .scene import LAYERS, classify_layer

__all__ = ["LAYERS", "classify_layer"]
