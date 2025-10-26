"""Index file management."""

import yaml
import logging
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional
from datetime import datetime
from packaging import version

logger = logging.getLogger(__name__)


def _represent_ordereddict(dumper, data):
    """Represent OrderedDict as a regular YAML mapping."""
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())


yaml.add_representer(OrderedDict, _represent_ordereddict)


@dataclass
class VersionEntry:
    """A single version entry in the index."""
    nixpkgs_commit: str
    commit_timestamp: str


@dataclass
class PackageIndex:
    """Index for a single package."""
    versions: Dict[str, VersionEntry] = field(default_factory=OrderedDict)


@dataclass
class Index:
    """Main index structure."""
    pkgs: Dict[str, PackageIndex] = field(default_factory=OrderedDict)

    @classmethod
    def load(cls, path: Path) -> "Index":
        """Load index from a YAML file, or create empty if it doesn't exist."""
        if not path.exists():
            logger.debug(f"Index file doesn't exist, creating new")
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        index = cls()
        total_versions = 0
        for pkg_name, pkg_data in data.get("pkgs", {}).items():
            pkg_index = PackageIndex()
            for version, version_data in pkg_data.items():
                pkg_index.versions[version] = VersionEntry(
                    nixpkgs_commit=version_data["nixpkgs_commit"],
                    commit_timestamp=version_data["commit_timestamp"]
                )
                total_versions += 1
            index.pkgs[pkg_name] = pkg_index
            logger.debug(f"  {pkg_name}: {len(pkg_index.versions)} versions")

        logger.info(f"Loaded {len(index.pkgs)} packages with {total_versions} total versions")
        return index

    def save(self, path: Path) -> None:
        """Save index to a YAML file."""
        data = {"pkgs": OrderedDict()}
        total_versions = 0
        for pkg_name in sorted(self.pkgs.keys()):
            pkg_index = self.pkgs[pkg_name]
            data["pkgs"][pkg_name] = OrderedDict()
            sorted_versions = sorted(pkg_index.versions.keys(), key=version.parse, reverse=True)
            for ver in sorted_versions:
                entry = pkg_index.versions[ver]
                data["pkgs"][pkg_name][ver] = asdict(entry)
                total_versions += 1

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.debug(f"Saved index: {len(self.pkgs)} packages, {total_versions} versions")

    def update_version(
        self,
        package: str,
        version: str,
        commit_sha: str,
        timestamp: str
    ) -> bool:
        """
        Update or add a version entry.
        Returns True if the entry was updated, False if it already had a newer timestamp.
        """
        if package not in self.pkgs:
            self.pkgs[package] = PackageIndex()

        if version not in self.pkgs[package].versions:
            self.pkgs[package].versions[version] = VersionEntry(
                nixpkgs_commit=commit_sha,
                commit_timestamp=timestamp
            )
            return True

        # Update only if this commit is newer
        existing_entry = self.pkgs[package].versions[version]
        if timestamp > existing_entry.commit_timestamp:
            old_commit = existing_entry.nixpkgs_commit
            self.pkgs[package].versions[version] = VersionEntry(
                nixpkgs_commit=commit_sha,
                commit_timestamp=timestamp
            )
            logger.debug(f"Updated: {package}:{version} ({old_commit[:12]} -> {commit_sha[:12]})")
            return True

        return False
