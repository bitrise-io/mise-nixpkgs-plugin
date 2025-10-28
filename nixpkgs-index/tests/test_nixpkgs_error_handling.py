"""Tests for Nix evaluation error handling."""

import pytest
from nixpkgs_index.nixpkgs import NixpkgsRepo
from pathlib import Path


class TestErrorDetection:
    """Test known error detection and message extraction."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create a NixpkgsRepo instance for testing."""
        return NixpkgsRepo(tmp_path / "nixpkgs")

    def test_is_known_error_attribute_not_found(self, repo):
        """Test detection of attribute not found errors."""
        stderr = """error: attribute 'python38' in selection path 'python38.version' not found inside path '', whose contents are: { _type = "pkgs"; "7z2hashcat" = «thunk»; }
       Did you mean one of python3, python, python2, python27 or python310?"""

        assert repo._is_known_eval_error(stderr)

    def test_is_known_error_attribute_deprecated(self, repo):
        """Test detection of attribute not found errors."""
        stderr = """error:
       … while evaluating an expression to select 'recurseForDerivations' on it
         at /nix/store/dnlyf0rsw59yk2cbazhagm62kbjcp3cc-source/pkgs/top-level/aliases.nix:27:8:
           26|     alias:
           27|     if alias.recurseForDerivations or false then
             |        ^
           28|       lib.removeAttrs alias [ "recurseForDerivations" ]

       … while evaluating alias
         at /nix/store/dnlyf0rsw59yk2cbazhagm62kbjcp3cc-source/pkgs/top-level/aliases.nix:27:8:
           26|     alias:
           27|     if alias.recurseForDerivations or false then
             |        ^
           28|       lib.removeAttrs alias [ "recurseForDerivations" ]

       (stack trace truncated; use '--show-trace' to show the full trace)

       error: ruby_3_1 has been removed, as it is has reached end‐of‐life upstream"""

        assert repo._is_known_eval_error(stderr)
