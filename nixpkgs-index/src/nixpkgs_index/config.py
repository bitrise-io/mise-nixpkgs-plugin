"""Configuration file parsing for the indexer."""

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, TypedDict, NotRequired, Required, Any, Optional, cast

logger = logging.getLogger(__name__)


class PackageConfigDict(TypedDict, total=False):
    nixpkgs_attributes: List[str]
    tests: List[str]


class EvalConfigDict(TypedDict, total=False):
    record_store_paths: bool
    systems: List[str]


class ConfigDict(TypedDict, total=False):
    branch: Required[str]
    pkgs: Required[Dict[str, PackageConfigDict]]
    eval: EvalConfigDict


@dataclass
class ParsedConfigYAML:
    branch: str
    pkgs: Dict[str, Any]
    eval: Optional[EvalConfigDict] = None


@dataclass
class PackageConfig:
    """Configuration for a single package."""

    nixpkgs_attributes: List[str]
    tests: List[str] = field(default_factory=list)


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
            raw_data = yaml.safe_load(f) or {}

        data = cast(ConfigDict, raw_data)

        if "branch" not in data:
            raise ValueError("Config file must specify 'branch'")
        if "pkgs" not in data:
            raise ValueError("Config file must specify 'pkgs'")

        parsed = ParsedConfigYAML(
            branch=data["branch"], pkgs=data["pkgs"], eval=data.get("eval")
        )

        logger.info(f"Branch: {parsed.branch}")

        pkgs = {}
        for pkg_name, pkg_data in parsed.pkgs.items():
            attributes = pkg_data.get("nixpkgs_attributes", [])
            tests = pkg_data.get("tests", [])
            logger.debug(
                f"Package '{pkg_name}': {len(attributes)} attributes, {len(tests)} tests"
            )
            pkgs[pkg_name] = PackageConfig(nixpkgs_attributes=attributes, tests=tests)

        logger.info(f"Loaded config with {len(pkgs)} packages")

        eval_data: EvalConfigDict = parsed.eval or {}
        record_store_paths = eval_data.get("record_store_paths", False)
        systems = eval_data.get("systems", [])
        eval_config = EvalConfig(record_store_paths=record_store_paths, systems=systems)

        if record_store_paths:
            logger.info(
                f"Store paths recording enabled for systems: {', '.join(systems)}"
            )

        return cls(branch=parsed.branch, pkgs=pkgs, eval=eval_config)
