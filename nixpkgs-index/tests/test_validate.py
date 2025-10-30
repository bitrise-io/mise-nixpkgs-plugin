"""Tests for the validation module."""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from nixpkgs_index.validate import (
    ValidationFailure,
    ValidationResult,
    StorePathValidator,
    TestValidator,
    validate_index,
    get_current_system,
)
from nixpkgs_index.index import Index, PackageIndex, VersionEntry
from nixpkgs_index.config import Config, PackageConfig, EvalConfig


class TestStorePathValidator:
    """Test StorePathValidator class."""

    def test_validate_success(self):
        validator = StorePathValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = validator.validate("/nix/store/abc-pkg", "x86_64-linux")
            assert result is True

    def test_validate_failure(self):
        validator = StorePathValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = validator.validate("/nix/store/abc-pkg", "x86_64-linux")
            assert result is False

    def test_validate_timeout(self):
        validator = StorePathValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutError()
            result = validator.validate("/nix/store/abc-pkg", "x86_64-linux")
            assert result is False

    def test_validate_exception(self):
        validator = StorePathValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command failed")
            result = validator.validate("/nix/store/abc-pkg", "x86_64-linux")
            assert result is False


class TestTestValidator:
    """Test TestValidator class."""

    def test_validate_no_tests(self):
        validator = TestValidator()
        result = validator.validate("3.4.0", [], "/nix/store/abc")
        assert result is None

    def test_validate_success(self):
        validator = TestValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = validator.validate("3.4.0", ["ruby --version"], "/nix/store/abc")
            assert result is None

    def test_validate_failure(self):
        validator = TestValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="error", stderr="")
            result = validator.validate("3.4.0", ["ruby --version"], "/nix/store/abc")
            assert result is not None
            assert "Test failed" in result

    def test_validate_timeout(self):
        validator = TestValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Timeout")
            result = validator.validate("3.4.0", ["ruby --version"], "/nix/store/abc")
            assert "Error running tests" in result

    def test_version_substitution(self):
        validator = TestValidator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            validator.validate("3.4.0", ["ruby --version | grep $VERSION"], "/nix/store/abc")
            # Check that the command was called with substituted version
            call_args = mock_run.call_args
            command = call_args[0][0][-1]  # Get the bash command
            assert "3.4.0" in command
            assert "$VERSION" not in command


class TestValidateIndex:
    """Test validate_index function."""

    def test_validate_index_no_failures(self):
        index = Index()
        index.pkgs["ruby"] = PackageIndex()
        index.pkgs["ruby"].versions["3.4.0"] = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-01T00:00:00Z",
            store_paths={"x86_64-linux": "/nix/store/abc-ruby-3.4.0"},
        )

        config = Config(
            branch="nixpkgs-unstable",
            pkgs={
                "ruby": PackageConfig(
                    nixpkgs_attributes=["ruby"],
                    tests=[],
                )
            },
        )

        with patch("nixpkgs_index.validate.get_current_system") as mock_system:
            mock_system.return_value = "x86_64-linux"
            with patch("nixpkgs_index.validate.StorePathValidator.validate") as mock_validate:
                mock_validate.return_value = True
                result = validate_index(index, config)

        assert not result.has_failures()
        assert result.validated_count == 1

    def test_validate_index_with_failures(self):
        index = Index()
        index.pkgs["ruby"] = PackageIndex()
        index.pkgs["ruby"].versions["3.4.0"] = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-01T00:00:00Z",
            store_paths={"x86_64-linux": "/nix/store/abc-ruby-3.4.0"},
        )

        config = Config(
            branch="nixpkgs-unstable",
            pkgs={
                "ruby": PackageConfig(
                    nixpkgs_attributes=["ruby"],
                    tests=[],
                )
            },
        )

        with patch("nixpkgs_index.validate.get_current_system") as mock_system:
            mock_system.return_value = "x86_64-linux"
            with patch("nixpkgs_index.validate.StorePathValidator.validate") as mock_validate:
                mock_validate.return_value = False
                result = validate_index(index, config)

        assert result.has_failures()
        assert len(result.failures) == 1

    def test_validate_index_with_target(self):
        index = Index()
        index.pkgs["ruby"] = PackageIndex()
        index.pkgs["ruby"].versions["3.4.0"] = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-01T00:00:00Z",
            store_paths={"x86_64-linux": "/nix/store/abc-ruby-3.4.0"},
        )
        index.pkgs["ruby"].versions["3.3.0"] = VersionEntry(
            nixpkgs_commit="def456",
            commit_timestamp="2025-01-02T00:00:00Z",
            store_paths={"x86_64-linux": "/nix/store/abc-ruby-3.3.0"},
        )

        config = Config(
            branch="nixpkgs-unstable",
            pkgs={
                "ruby": PackageConfig(
                    nixpkgs_attributes=["ruby"],
                    tests=[],
                )
            },
        )

        with patch("nixpkgs_index.validate.get_current_system") as mock_system:
            mock_system.return_value = "x86_64-linux"
            with patch("nixpkgs_index.validate.StorePathValidator.validate") as mock_validate:
                mock_validate.return_value = True
                result = validate_index(index, config, target="ruby@3.4.0")

        assert result.validated_count == 1

    def test_validate_index_invalid_target(self):
        index = Index()
        config = Config(
            branch="nixpkgs-unstable",
            pkgs={"ruby": PackageConfig(nixpkgs_attributes=["ruby"], tests=[])},
        )

        with pytest.raises(ValueError, match="Invalid target format"):
            validate_index(index, config, target="invalid-format")

    def test_validate_index_target_not_found(self):
        index = Index()
        index.pkgs["ruby"] = PackageIndex()
        index.pkgs["ruby"].versions["3.4.0"] = VersionEntry(
            nixpkgs_commit="abc123",
            commit_timestamp="2025-01-01T00:00:00Z",
            store_paths={"x86_64-linux": "/nix/store/abc-ruby-3.4.0"},
        )

        config = Config(
            branch="nixpkgs-unstable",
            pkgs={
                "ruby": PackageConfig(
                    nixpkgs_attributes=["ruby"],
                    tests=[],
                )
            },
        )

        with patch("nixpkgs_index.validate.get_current_system") as mock_system:
            mock_system.return_value = "x86_64-linux"
            with pytest.raises(ValueError, match="No matching package/version found"):
                validate_index(index, config, target="ruby@9.9.9")
