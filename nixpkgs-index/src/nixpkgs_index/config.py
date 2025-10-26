"""Configuration file parsing for the indexer."""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class PackageConfig:
    """Configuration for a single package."""
    nixpkgs_attributes: List[str]


@dataclass
class Config:
    """Main configuration structure."""
    branch: str
    pkgs: Dict[str, PackageConfig]

    @classmethod
    def load(cls, path: Path) -> "Config":
        """Load configuration from a YAML file."""
        logger.debug(f"Opening config file: {path}")
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data:
            logger.warning(f"Config file is empty or invalid YAML")
            data = {}

        branch = data.get("branch", "nixpkgs-unstable")
        logger.info(f"Branch: {branch}")

        pkgs = {}
        for pkg_name, pkg_data in data.get("pkgs", {}).items():
            attributes = pkg_data.get("nixpkgs_attributes", [])
            logger.debug(f"Package '{pkg_name}': {len(attributes)} attributes")
            pkgs[pkg_name] = PackageConfig(nixpkgs_attributes=attributes)

        logger.info(f"Loaded config with {len(pkgs)} packages")
        return cls(branch=branch, pkgs=pkgs)
