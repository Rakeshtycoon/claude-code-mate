"""Format-agnostic binary I/O framework."""
from .guid import Guid
from .hexdump import entropy_profile, hexdump, shannon_entropy
from .reader import BinaryReader

__all__ = ["Guid", "BinaryReader", "hexdump", "shannon_entropy", "entropy_profile"]
