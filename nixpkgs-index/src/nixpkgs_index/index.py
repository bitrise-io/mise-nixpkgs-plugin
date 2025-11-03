"""Index file management."""

import yaml
import json
import logging
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Any, TypedDict, NotRequired, Required, cast, Literal
from datetime import datetime
from packaging import version

logger = logging.getLogger(__name__)


class VersionEntryDict(TypedDict, total=False):
    nixpkgs_commit: Required[str]
    commit_timestamp: Required[str]
    store_paths: Dict[str, str]


class IndexDict(TypedDict, total=False):
    pkgs: Dict[str, Dict[str, VersionEntryDict]]


@dataclass
class ParsedVersionEntry:
    nixpkgs_commit: str
    commit_timestamp: str
    store_paths: Optional[Dict[str, str]] = None


@dataclass
class ParsedIndexYAML:
    pkgs: Dict[str, Dict[str, ParsedVersionEntry]]


def _represent_ordereddict(dumper, data):
    """Represent OrderedDict as a regular YAML mapping."""
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


yaml.add_representer(OrderedDict, _represent_ordereddict)


@dataclass
class VersionEntry:
    """A single version entry in the index."""

    nixpkgs_commit: str
    commit_timestamp: str
    store_paths: Optional[Dict[str, str]] = None


@dataclass
class PackageIndex:
    """Index for a single package."""

    versions: Dict[str, VersionEntry] = field(default_factory=OrderedDict)


@dataclass
class Index:
    """Main index structure."""

    pkgs: Dict[str, PackageIndex] = field(default_factory=OrderedDict)

    @classmethod
    def load(cls, path: Path, format: Optional[Literal["yml", "json"]] = None) -> "Index":
        """Load index from a file (yml or json), or create empty if it doesn't exist.

        If format is not specified, it will be auto-detected from the file extension.
        """
        if not path.exists():
            logger.debug(f"Index file doesn't exist, creating new")
            return cls()

        # Auto-detect format from file extension if not specified
        if format is None:
            ext = path.suffix.lower()
            if ext == ".json":
                format = "json"
            elif ext in (".yaml", ".yml"):
                format = "yml"
            else:
                format = "yml"

        with open(path) as f:
            if format == "json":
                raw_data = json.load(f) or {}
            else:
                raw_data = yaml.safe_load(f) or {}

        data = cast(IndexDict, raw_data)

        pkgs_data = data.get("pkgs") or {}
        parsed_pkgs: Dict[str, Dict[str, ParsedVersionEntry]] = {}
        for pkg_name, pkg_data in pkgs_data.items():
            parsed_versions: Dict[str, ParsedVersionEntry] = {}
            for ver, version_data in pkg_data.items():
                parsed_versions[ver] = ParsedVersionEntry(
                    nixpkgs_commit=version_data["nixpkgs_commit"],
                    commit_timestamp=version_data["commit_timestamp"],
                    store_paths=version_data.get("store_paths"),
                )
            parsed_pkgs[pkg_name] = parsed_versions

        parsed = ParsedIndexYAML(pkgs=parsed_pkgs)

        index = cls()
        total_versions = 0
        for pkg_name, parsed_versions in parsed.pkgs.items():
            pkg_index = PackageIndex()
            for ver, parsed_entry in parsed_versions.items():
                pkg_index.versions[ver] = VersionEntry(
                    nixpkgs_commit=parsed_entry.nixpkgs_commit,
                    commit_timestamp=parsed_entry.commit_timestamp,
                    store_paths=parsed_entry.store_paths,
                )
                total_versions += 1
            index.pkgs[pkg_name] = pkg_index
            logger.debug(f"  {pkg_name}: {len(pkg_index.versions)} versions")

        logger.info(
            f"Loaded {len(index.pkgs)} packages with {total_versions} total versions"
        )
        return index

    def save(self, path: Path, format: Literal["yml", "json"] = "yml") -> None:
        """Save index to a file in the specified format (yml or json)."""
        data = {"pkgs": OrderedDict()}
        total_versions = 0
        for pkg_name in sorted(self.pkgs.keys()):
            pkg_index = self.pkgs[pkg_name]
            data["pkgs"][pkg_name] = OrderedDict()
            sorted_versions = sorted(
                pkg_index.versions.keys(), key=version.parse, reverse=True
            )
            for ver in sorted_versions:
                entry = pkg_index.versions[ver]
                entry_dict = asdict(entry)
                if entry_dict.get("store_paths") is None:
                    del entry_dict["store_paths"]
                data["pkgs"][pkg_name][ver] = entry_dict
                total_versions += 1

        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.debug(
            f"Saved index ({format.upper()}): {len(self.pkgs)} packages, {total_versions} versions"
        )

    def update_version(
        self,
        package: str,
        version: str,
        commit_sha: str,
        timestamp: str,
        store_paths: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Update or add a version entry.
        Returns True if the entry was updated, False if it already had a newer timestamp
        or if the store object hasn't changed.
        """
        if package not in self.pkgs:
            self.pkgs[package] = PackageIndex()

        if version not in self.pkgs[package].versions:
            self.pkgs[package].versions[version] = VersionEntry(
                nixpkgs_commit=commit_sha,
                commit_timestamp=timestamp,
                store_paths=store_paths,
            )
            return True

        # Update only if this commit is newer
        existing_entry = self.pkgs[package].versions[version]
        if timestamp > existing_entry.commit_timestamp:
            # Check if store objects actually changed
            if self._should_update_based_on_store_paths(
                existing_entry.store_paths, store_paths
            ):
                old_commit = existing_entry.nixpkgs_commit
                self.pkgs[package].versions[version] = VersionEntry(
                    nixpkgs_commit=commit_sha,
                    commit_timestamp=timestamp,
                    store_paths=store_paths,
                )
                logger.debug(
                    f"Updated: {package}:{version} ({old_commit[:12]} -> {commit_sha[:12]})"
                )
                return True
            else:
                logger.debug(f"Skipped: {package}:{version} (store objects unchanged)")
                return False

        return False

    def _should_update_based_on_store_paths(
        self,
        old_store_paths: Optional[Dict[str, str]],
        new_store_paths: Optional[Dict[str, str]],
    ) -> bool:
        """
        Determine if an update should proceed based on store path comparison.

        Returns True if:
        - Store paths changed
        - Unable to compare (missing in index or new entry), with warning

        Returns False if:
        - Both have store paths and they match
        """
        # If old entry has no store paths, we can't optimize - do the update
        if old_store_paths is None:
            if new_store_paths is not None:
                logger.warning(
                    "No store paths in index entry, updating with store paths from new commit"
                )
            return True

        # If new entry has no store paths, we can't compare - do the update
        if new_store_paths is None:
            logger.warning("No store paths in new entry, proceeding with commit update")
            return True

        # Both have store paths - compare them
        # Store paths match if all systems are identical
        if old_store_paths == new_store_paths:
            return False

        # Store paths differ - check if it's just missing systems
        old_systems = set(old_store_paths.keys())
        new_systems = set(new_store_paths.keys())

        if old_systems != new_systems:
            logger.warning(
                f"Store paths evaluated for different systems: "
                f"old={sorted(old_systems)}, new={sorted(new_systems)}. "
                f"Proceeding with commit update."
            )
            return True

        # Same systems but different paths - the store object changed
        return True
