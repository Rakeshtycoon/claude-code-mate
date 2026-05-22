"""Qt desktop viewer.

Importing this package does not require PySide6/pyvistaqt; those are only
needed when :func:`advrecover.viewer.app.launch` is actually called. The
scene model (:mod:`advrecover.viewer.scene`) is Qt-free and testable.
"""
from .scene import LAYER_ORDER, SceneLayer, SceneModel, build_scene

__all__ = ["build_scene", "SceneModel", "SceneLayer", "LAYER_ORDER"]
