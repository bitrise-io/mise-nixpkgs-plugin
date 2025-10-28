"""Nixpkgs repository management."""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NixpkgsRepo:
    """Manages a local nixpkgs repository with shallow fetching."""

    def __init__(self, repo_path: Path, branch: str = "nixpkgs-unstable"):
        self.repo_path = repo_path
        self.branch = branch

    def ensure_initialized(self) -> None:
        """
        Initialize the nixpkgs repository with sparse-checkout.
        Sets up an empty repo that can fetch specific commits.
        """
        if self.repo_path.exists():
            logger.debug(f"Repository already exists at {self.repo_path}")
            return

        logger.info(f"Initializing nixpkgs repository at {self.repo_path}")
        self.repo_path.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["git", "init"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/NixOS/nixpkgs.git"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        logger.debug("Configuring sparse-checkout for pkgs and lib directories")
        subprocess.run(
            ["git", "sparse-checkout", "init", "--cone"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        subprocess.run(
            ["git", "sparse-checkout", "set", "pkgs", "lib"],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )

        logger.info("Repository initialized successfully")

    def fetch_and_checkout_commit(self, commit_sha: str) -> None:
        """
        Fetch a specific commit shallowly and check it out.
        This is the core operation for the new approach.
        """
        logger.info(f"Fetching commit: {commit_sha[:12]}")

        try:
            subprocess.run(
                ["git", "fetch", "--depth", "1", "origin", commit_sha],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch commit {commit_sha[:12]}: {e.stderr}")
            raise

        logger.debug(f"Checking out FETCH_HEAD")
        subprocess.run(
            ["git", "checkout", "FETCH_HEAD"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
        )

    def evaluate_attribute(self, attribute: str) -> Optional[str]:
        """
        Evaluate a nixpkgs attribute and return its version.
        Returns None if evaluation fails.
        """
        try:
            result = subprocess.run(
                ["nix", "eval", "--file", ".", f"{attribute}.version", "--raw"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.debug(f"Eval {attribute}.version: {version}")
                return version
            else:
                logger.warning(f"Nix eval failed for {attribute}: {result.stderr.strip()}")
                return None
        except subprocess.TimeoutExpired:
            logger.debug(f"Evaluation timeout: {attribute}")
            return None
        except Exception as e:
            logger.debug(f"Evaluation error for {attribute}: {e}")
            return None

    def evaluate_attribute_store_path(self, attribute: str, system: str) -> Optional[str]:
        """
        Evaluate a nixpkgs attribute for a specific system and return its store path.
        Returns None if evaluation fails.
        """
        try:
            result = subprocess.run(
                ["nix", "eval", "--file", ".", attribute, "--raw", "--system", system],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                store_path = result.stdout.strip()
                logger.debug(f"Eval {attribute} ({system}): {store_path}")
                return store_path
            else:
                logger.warning(f"Nix eval failed for {attribute} on {system}: {result.stderr.strip()}")
                return None
        except subprocess.TimeoutExpired:
            logger.debug(f"Evaluation timeout: {attribute} on {system}")
            return None
        except Exception as e:
            logger.debug(f"Evaluation error for {attribute} on {system}: {e}")
            return None

