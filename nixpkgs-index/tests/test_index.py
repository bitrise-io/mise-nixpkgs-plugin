"""Unit tests for index module."""

import pytest
import tempfile
from pathlib import Path
from collections import OrderedDict
from nixpkgs_index.index import Index, PackageIndex, VersionEntry


class TestPackageIndex:
    def test_create_empty_package_index(self):
        pkg_index = PackageIndex()
        assert len(pkg_index.versions) == 0
        assert isinstance(pkg_index.versions, OrderedDict)


    def test_package_index_version_lookup(self):
        pkg_index = PackageIndex()
        entry = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-15T12:00:00+00:00"
        )
        pkg_index.versions["3.3.9"] = entry

        assert "3.3.9" in pkg_index.versions
        assert "3.3.8" not in pkg_index.versions
        assert pkg_index.versions.get("3.3.9") == entry
        assert pkg_index.versions.get("nonexistent") is None

    def test_package_index_multiple_versions(self):
        pkg_index = PackageIndex()

        # Add versions
        for i, version in enumerate(["3.3.9", "3.3.8", "3.3.7"]):
            pkg_index.versions[version] = VersionEntry(
                nixpkgs_commit=f"commit{i}",
                commit_timestamp="2025-01-01T00:00:00+00:00"
            )

        assert len(pkg_index.versions) == 3
        assert all(v in pkg_index.versions for v in ["3.3.9", "3.3.8", "3.3.7"])


class TestIndex:
    def test_create_empty_index(self):
        index = Index()
        assert len(index.pkgs) == 0
        assert isinstance(index.pkgs, OrderedDict)


    def test_update_version_new_package(self):
        index = Index()

        updated = index.update_version(
            package="ruby",
            version="3.3.9",
            commit_sha="abc123",
            timestamp="2025-01-15T12:00:00+00:00"
        )

        assert updated is True
        assert "ruby" in index.pkgs
        assert "3.3.9" in index.pkgs["ruby"].versions
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "abc123"

    def test_update_version_new_version(self):
        index = Index()

        index.update_version("ruby", "3.3.9", "commit1", "2025-01-15T12:00:00+00:00")
        updated = index.update_version("ruby", "3.3.8", "commit2", "2025-01-14T12:00:00+00:00")

        assert updated is True
        assert len(index.pkgs["ruby"].versions) == 2
        assert "3.3.8" in index.pkgs["ruby"].versions

    def test_update_version_existing_version_newer(self):
        index = Index()

        index.update_version("ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00")
        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00"
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_update_version_existing_version_older(self):
        index = Index()

        index.update_version("ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00")
        updated = index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00"
        )

        assert updated is False
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_update_version_same_timestamp(self):
        index = Index()

        timestamp = "2025-01-15T12:00:00+00:00"
        index.update_version("ruby", "3.3.9", "commit1", timestamp)
        updated = index.update_version("ruby", "3.3.9", "commit2", timestamp)

        assert updated is False
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "commit1"

    def test_load_empty_index_from_nonexistent_file(self):
        nonexistent_path = Path("/tmp/does_not_exist_xyz123.yaml")
        index = Index.load(nonexistent_path)

        assert len(index.pkgs) == 0

    def test_save_and_load_roundtrip(self):
        index1 = Index()
        index1.update_version("ruby", "3.3.9", "commit1", "2025-01-15T12:00:00+00:00")
        index1.update_version("ruby", "3.3.8", "commit2", "2025-01-14T12:00:00+00:00")
        index1.update_version("python", "3.11.7", "commit3", "2025-01-13T12:00:00+00:00")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index1.save(output_path)
            index2 = Index.load(output_path)

            assert len(index2.pkgs) == 2
            assert len(index2.pkgs["ruby"].versions) == 2
            assert len(index2.pkgs["python"].versions) == 1

            assert index2.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "commit1"
            assert index2.pkgs["ruby"].versions["3.3.8"].nixpkgs_commit == "commit2"
            assert index2.pkgs["python"].versions["3.11.7"].nixpkgs_commit == "commit3"
        finally:
            output_path.unlink()


    def test_load_empty_yaml_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            path = Path(f.name)

        try:
            index = Index.load(path)
            assert len(index.pkgs) == 0
        finally:
            path.unlink()

    def test_yaml_has_versions_sorted_descending(self):
        index = Index()

        # Add versions in non-sorted order
        index.update_version("ruby", "3.3.7", "c1", "2025-01-13T12:00:00+00:00")
        index.update_version("ruby", "3.3.9", "c2", "2025-01-15T12:00:00+00:00")
        index.update_version("ruby", "3.3.8", "c3", "2025-01-14T12:00:00+00:00")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            yaml_content = output_path.read_text()

            # Find positions of version strings
            v3_3_9_pos = yaml_content.find("3.3.9")
            v3_3_8_pos = yaml_content.find("3.3.8")
            v3_3_7_pos = yaml_content.find("3.3.7")

            # Versions should appear in descending order
            assert v3_3_9_pos < v3_3_8_pos < v3_3_7_pos
        finally:
            output_path.unlink()

    def test_yaml_structure_with_multiple_packages_and_versions(self):
        index = Index()

        # Add data in scrambled order
        index.update_version("zebra", "2.0", "z2", "2025-01-16T12:00:00+00:00")
        index.update_version("apple", "1.2", "a2", "2025-01-14T12:00:00+00:00")
        index.update_version("apple", "1.1", "a1", "2025-01-13T12:00:00+00:00")
        index.update_version("zebra", "1.9", "z1", "2025-01-15T12:00:00+00:00")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            yaml_content = output_path.read_text()

            # Packages should be alphabetically sorted
            apple_pos = yaml_content.find("apple:")
            zebra_pos = yaml_content.find("zebra:")
            assert apple_pos < zebra_pos

            # Within each package, find the version ordering
            # Apple versions should be descending
            apple_section = yaml_content[apple_pos:zebra_pos]
            apple_v1_2_pos = apple_section.find("1.2")
            apple_v1_1_pos = apple_section.find("1.1")
            assert apple_v1_2_pos < apple_v1_1_pos
        finally:
            output_path.unlink()
