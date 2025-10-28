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

    def test_semantic_version_sorting_with_double_digit_minor(self):
        """Test that versions like 24.10.0 sort correctly before 24.5.0 (not after)."""
        index = Index()

        # Add versions in non-sorted order with double-digit minor versions
        index.update_version("node", "24.5.0", "c1", "2025-08-25T22:56:36+00:00")
        index.update_version("node", "24.10.0", "c2", "2025-10-23T22:54:49+00:00")
        index.update_version("node", "24.9.0", "c3", "2025-10-09T22:52:58+00:00")
        index.update_version("node", "22.20.0", "c4", "2025-10-23T22:54:49+00:00")
        index.update_version("node", "22.19.0", "c5", "2025-10-21T23:04:44+00:00")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            yaml_content = output_path.read_text()

            # Find positions of version strings
            v24_10_pos = yaml_content.find("24.10.0")
            v24_9_pos = yaml_content.find("24.9.0")
            v24_5_pos = yaml_content.find("24.5.0")
            v22_20_pos = yaml_content.find("22.20.0")
            v22_19_pos = yaml_content.find("22.19.0")

            # Versions should appear in descending semantic order
            assert v24_10_pos < v24_9_pos < v24_5_pos < v22_20_pos < v22_19_pos
        finally:
            output_path.unlink()


class TestStorePaths:
    def test_update_version_with_store_paths(self):
        index = Index()
        store_paths = {
            "x86_64-linux": "/nix/store/abc123...-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456...-ruby-3.3.9"
        }

        updated = index.update_version(
            package="ruby",
            version="3.3.9",
            commit_sha="commit1",
            timestamp="2025-01-15T12:00:00+00:00",
            store_paths=store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].store_paths == store_paths

    def test_update_version_without_store_paths(self):
        index = Index()

        updated = index.update_version(
            package="ruby",
            version="3.3.9",
            commit_sha="commit1",
            timestamp="2025-01-15T12:00:00+00:00"
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].store_paths is None

    def test_version_entry_with_store_paths(self):
        entry = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-15T12:00:00+00:00",
            store_paths={
                "x86_64-linux": "/nix/store/path1",
                "aarch64-darwin": "/nix/store/path2"
            }
        )

        assert entry.store_paths is not None
        assert len(entry.store_paths) == 2
        assert entry.store_paths["x86_64-linux"] == "/nix/store/path1"

    def test_save_and_load_with_store_paths(self):
        index1 = Index()
        store_paths_ruby = {
            "x86_64-linux": "/nix/store/abc123...-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456...-ruby-3.3.9"
        }
        store_paths_python = {
            "x86_64-linux": "/nix/store/ghi789...-python-3.11.7",
            "aarch64-darwin": "/nix/store/jkl012...-python-3.11.7"
        }

        index1.update_version(
            "ruby", "3.3.9", "commit1", "2025-01-15T12:00:00+00:00",
            store_paths=store_paths_ruby
        )
        index1.update_version(
            "python", "3.11.7", "commit2", "2025-01-14T12:00:00+00:00",
            store_paths=store_paths_python
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index1.save(output_path)
            index2 = Index.load(output_path)

            assert index2.pkgs["ruby"].versions["3.3.9"].store_paths == store_paths_ruby
            assert index2.pkgs["python"].versions["3.11.7"].store_paths == store_paths_python
        finally:
            output_path.unlink()

    def test_save_omits_none_store_paths(self):
        """Ensure that store_paths field is not written when None."""
        index = Index()
        index.update_version(
            "ruby", "3.3.9", "commit1", "2025-01-15T12:00:00+00:00"
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            yaml_content = output_path.read_text()

            # Verify store_paths is NOT in the YAML when it's None
            assert "store_paths:" not in yaml_content
        finally:
            output_path.unlink()

    def test_save_includes_store_paths_in_yaml(self):
        """Ensure that store_paths field is included in YAML when present."""
        index = Index()
        store_paths = {"x86_64-linux": "/nix/store/path1"}
        index.update_version(
            "ruby", "3.3.9", "commit1", "2025-01-15T12:00:00+00:00",
            store_paths=store_paths
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            yaml_content = output_path.read_text()

            # Verify store_paths IS in the YAML when present
            assert "store_paths:" in yaml_content
            assert "x86_64-linux:" in yaml_content
            assert "/nix/store/path1" in yaml_content
        finally:
            output_path.unlink()

    def test_update_version_with_store_paths_replaces_on_newer(self):
        """Test that store_paths are replaced when updating to a newer commit."""
        index = Index()

        old_store_paths = {"x86_64-linux": "/nix/store/old-path"}
        new_store_paths = {"x86_64-linux": "/nix/store/new-path"}

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=old_store_paths
        )
        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].store_paths == new_store_paths

    def test_mixed_entries_with_and_without_store_paths(self):
        """Test that index can handle mix of entries with and without store_paths."""
        index = Index()

        index.update_version("ruby", "3.3.9", "c1", "2025-01-15T12:00:00+00:00")
        index.update_version(
            "ruby", "3.3.8", "c2", "2025-01-14T12:00:00+00:00",
            store_paths={"x86_64-linux": "/nix/store/path1"}
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            output_path = Path(f.name)

        try:
            index.save(output_path)
            index2 = Index.load(output_path)

            assert index2.pkgs["ruby"].versions["3.3.9"].store_paths is None
            assert index2.pkgs["ruby"].versions["3.3.8"].store_paths is not None
            assert index2.pkgs["ruby"].versions["3.3.8"].store_paths["x86_64-linux"] == "/nix/store/path1"
        finally:
            output_path.unlink()


class TestStorePathOptimization:
    """Tests for store path comparison optimization in commit updates."""

    def test_store_paths_unchanged_skip_update(self):
        """When store paths match, update should be skipped even with newer timestamp."""
        index = Index()
        store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=store_paths
        )

        assert updated is False
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "old_commit"

    def test_store_paths_changed_do_update(self):
        """When store paths differ, update should proceed."""
        index = Index()
        old_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }
        new_store_paths = {
            "x86_64-linux": "/nix/store/xyz789-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=old_store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_old_entry_no_store_paths_new_has_them_do_update(self):
        """When old entry has no store paths, update should proceed."""
        index = Index()

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00"
        )

        new_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_old_entry_has_store_paths_new_has_none_do_update(self):
        """When new entry has no store paths, update should proceed."""
        index = Index()

        old_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=old_store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00"
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_different_systems_between_old_and_new_do_update(self):
        """When store paths have different systems, update should proceed with warning."""
        index = Index()

        old_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9"
        }
        new_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=old_store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_single_path_changed_in_multi_system_do_update(self):
        """When one of multiple store paths changes, update should proceed."""
        index = Index()

        old_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }
        new_store_paths = {
            "x86_64-linux": "/nix/store/xyz789-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=old_store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_neither_has_store_paths_timestamp_comparison_applies(self):
        """When neither has store paths, normal timestamp comparison applies."""
        index = Index()

        index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00"
        )

        updated = index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00"
        )

        assert updated is True
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"

    def test_old_timestamp_prevents_update_regardless_of_store_paths(self):
        """When new timestamp is older, update should not happen."""
        index = Index()

        old_store_paths = {
            "x86_64-linux": "/nix/store/abc123-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/def456-ruby-3.3.9"
        }
        new_store_paths = {
            "x86_64-linux": "/nix/store/xyz789-ruby-3.3.9",
            "aarch64-darwin": "/nix/store/xyz000-ruby-3.3.9"
        }

        index.update_version(
            "ruby", "3.3.9", "new_commit", "2025-01-16T12:00:00+00:00",
            store_paths=old_store_paths
        )

        updated = index.update_version(
            "ruby", "3.3.9", "old_commit", "2025-01-15T12:00:00+00:00",
            store_paths=new_store_paths
        )

        assert updated is False
        assert index.pkgs["ruby"].versions["3.3.9"].nixpkgs_commit == "new_commit"
