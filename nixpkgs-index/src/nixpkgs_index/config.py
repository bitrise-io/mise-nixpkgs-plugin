"""Configuration file parsing for the indexer."""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class PackageConfig:
    """Configuration for a single package."""
    nixpkgs_attributes: List[str]


@dataclass
class EvalConfig:
    """Evaluation settings configuration."""
    record_store_paths: bool = False
    systems: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration structure."""
    branch: str
    pkgs: Dict[str, PackageConfig]
    eval: EvalConfig = field(default_factory=EvalConfig)

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

        eval_data = data.get("eval", {})
        record_store_paths = eval_data.get("record_store_paths", False)
        systems = eval_data.get("systems", [])
        eval_config = EvalConfig(record_store_paths=record_store_paths, systems=systems)

        if record_store_paths:
            logger.info(f"Store paths recording enabled for systems: {', '.join(systems)}")

        return cls(branch=branch, pkgs=pkgs, eval=eval_config)
