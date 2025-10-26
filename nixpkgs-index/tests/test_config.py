"""Unit tests for config module."""

import pytest
import tempfile
from pathlib import Path
from nixpkgs_index.config import Config, PackageConfig


class TestPackageConfig:
    def test_create_package_config(self):
        attrs = ["ruby", "ruby_3_4", "ruby_3_3"]
        config = PackageConfig(nixpkgs_attributes=attrs)

        assert config.nixpkgs_attributes == attrs

    def test_empty_attributes(self):
        config = PackageConfig(nixpkgs_attributes=[])
        assert config.nixpkgs_attributes == []


class TestConfig:
    def test_load_valid_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
branch: nixpkgs-unstable
pkgs:
  ruby:
    nixpkgs_attributes:
      - ruby
      - ruby_3_4
      - ruby_3_3
  python:
    nixpkgs_attributes:
      - python3
      - python3_11
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)

            assert config.branch == "nixpkgs-unstable"
            assert len(config.pkgs) == 2
            assert "ruby" in config.pkgs
            assert "python" in config.pkgs

            assert config.pkgs["ruby"].nixpkgs_attributes == ["ruby", "ruby_3_4", "ruby_3_3"]
            assert config.pkgs["python"].nixpkgs_attributes == ["python3", "python3_11"]
        finally:
            config_path.unlink()

    def test_load_config_with_default_branch(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
pkgs:
  ruby:
    nixpkgs_attributes:
      - ruby
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.branch == "nixpkgs-unstable"
        finally:
            config_path.unlink()

    def test_load_config_with_custom_branch(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
branch: nixpkgs
pkgs:
  ruby:
    nixpkgs_attributes:
      - ruby
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.branch == "nixpkgs"
        finally:
            config_path.unlink()

    def test_load_empty_config_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.branch == "nixpkgs-unstable"
            assert len(config.pkgs) == 0
        finally:
            config_path.unlink()

    def test_load_config_with_no_packages(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
branch: nixpkgs-unstable
pkgs: {}
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.branch == "nixpkgs-unstable"
            assert len(config.pkgs) == 0
        finally:
            config_path.unlink()

    def test_load_nonexistent_file(self):
        nonexistent_path = Path("/tmp/this_does_not_exist_xyz123.yaml")

        with pytest.raises(FileNotFoundError):
            Config.load(nonexistent_path)

    def test_config_with_multiple_packages(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
branch: main
pkgs:
  ruby:
    nixpkgs_attributes:
      - ruby
  python:
    nixpkgs_attributes:
      - python3
  nodejs:
    nixpkgs_attributes:
      - nodejs
  go:
    nixpkgs_attributes:
      - go
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert len(config.pkgs) == 4
            assert all(pkg in config.pkgs for pkg in ["ruby", "python", "nodejs", "go"])
        finally:
            config_path.unlink()

    def test_config_with_empty_attributes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
pkgs:
  ruby:
    nixpkgs_attributes: []
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.pkgs["ruby"].nixpkgs_attributes == []
        finally:
            config_path.unlink()

    def test_config_with_missing_attributes_field(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
pkgs:
  ruby: {}
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = Config.load(config_path)
            assert config.pkgs["ruby"].nixpkgs_attributes == []
        finally:
            config_path.unlink()
