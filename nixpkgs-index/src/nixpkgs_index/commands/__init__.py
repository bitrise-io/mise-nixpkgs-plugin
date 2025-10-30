"""CLI commands for nixpkgs-index."""

from .index import index
from .validate import validate

__all__ = ["index", "validate"]
