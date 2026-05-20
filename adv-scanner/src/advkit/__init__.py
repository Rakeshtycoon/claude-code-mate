"""advkit - reverse-engineering & analysis toolkit for ``.adv`` diamond
galaxy-scanner files.

Layered architecture (clean dependency direction, low -> high):

    core        memory-mapped IO, logging
    parsers     JPEG carving, binary inspection, the .adv container model
    volume      voxel-volume reconstruction, automated structure discovery
    mesh        isosurface extraction and mesh export
    inclusion   volumetric defect detection
    tools       the ``adv-analyzer`` command-line front end

Every layer depends only on the ones above it. See ``docs/`` for the
reverse-engineering write-up (``FORMAT.md``) and the phased delivery plan
(``ROADMAP.md``).
"""
from advkit.parsers import AdvFile

__version__ = "0.1.0"
__all__ = ["AdvFile", "__version__"]
