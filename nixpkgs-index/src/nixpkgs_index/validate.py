"""Validation module for checking index integrity and package correctness."""

import subprocess
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from .index import Index
from .config import Config

logger = logging.getLogger(__name__)


def get_current_system() -> str:
    """
    Get the current system ID using nix eval.

    Returns the system string (e.g., 'x86_64-linux', 'aarch64-darwin') or raises
    an exception if the command fails.
    """
    try:
        result = subprocess.run(
            [
                "nix",
                "eval",
                "--impure",
                "--expr",
                "builtins.currentSystem",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to get current system: {result.stderr or result.stdout}"
            )
        return result.stdout.strip().strip('"')
    except subprocess.TimeoutExpired:
        raise RuntimeError("Getting current system timed out")
    except Exception as e:
        raise RuntimeError(f"Error getting current system: {e}")


@dataclass
class ValidationFailure:
    """A single validation failure."""

    package: str
    version: str
    store_path: Optional[str]
    system: Optional[str]
    error: str


@dataclass
class ValidationResult:
    """Result of a validation run."""

    failures: List[ValidationFailure] = field(default_factory=list)
    total_packages: int = 0
    total_versions: int = 0
    validated_count: int = 0

    def has_failures(self) -> bool:
        """Check if there are any failures."""
        return len(self.failures) > 0

    def add_failure(
        self,
        package: str,
        version: str,
        error: str,
        store_path: Optional[str] = None,
        system: Optional[str] = None,
    ) -> None:
        """Add a validation failure."""
        self.failures.append(
            ValidationFailure(
                package=package,
                version=version,
                store_path=store_path,
                system=system,
                error=error,
            )
        )

    def summary(self) -> str:
        """Get a summary of the validation result."""
        if self.has_failures():
            return f"FAILED: {len(self.failures)} failures out of {self.validated_count} validated versions"
        else:
            return f"PASSED: All {self.validated_count} versions validated successfully"


class StorePathValidator:
    def __init__(self):
        pass

    def validate(self, store_path: str, system: str) -> bool:
        """
        Validate a store path using nix build.

        Command: `nix build --option max-jobs 0 --no-link <store-path>`

        Flags:
            --option max-jobs 0
                Disable local parallel builds. This is critical because:
                - We want to fetch from substituters only (binary caches), not build locally
                - Setting to 0 prevents local builds and forces cache lookups
                - Validates that the store path is available in configured substituters

            --no-link
                Don't create a symlink to the build result. Since we only care about
                validation (whether the path exists and can be fetched), we don't need
                the result. This saves disk space and is faster.

        Returns True if validation succeeded, False otherwise.
        """
        try:
            result = subprocess.run(
                [
                    "nix",
                    "build",
                    "--option",
                    "max-jobs",
                    "0",
                    "--no-link",
                    store_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error(f"Store path validation timed out for {store_path}")
            return False
        except Exception as e:
            logger.error(f"Error validating store path {store_path}: {e}")
            return False


class TestValidator:
    def validate(
        self, version: str, tests: List[str], store_path: str
    ) -> Optional[str]:
        """
        Run tests for a package using its store path from the index.

        Command: `nix shell <store-path> -c bash -c <test-commands>`

        Flags:
            <store-path>
                The exact store path from the index to test. This ensures we're
                testing the actual indexed artifact, not a fresh build from nixpkgs.
                Makes validation reproducible and verifies index integrity.

            -c <command>
                Execute the command in the nix-shell environment. This puts the
                packages from store_path on PATH and available to the tests.

        Test execution:
            - Tests are bash scripts defined in the config (see example-config.yml)
            - `$VERSION` in test commands is replaced with the actual version
            - Tests run with `set -e` so any failure stops execution immediately

        Returns None if all tests pass, error message otherwise.
        """
        if not tests:
            return None

        test_commands = "set -e\n"
        for test in tests:
            test_cmd = test.replace("$VERSION", version)
            test_commands += f"{test_cmd}\n"

        try:
            result = subprocess.run(
                [
                    "nix",
                    "shell",
                    store_path,
                    "-c",
                    "bash",
                    "-c",
                    test_commands,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return f"Test failed: {result.stderr or result.stdout}"
            return None
        except subprocess.TimeoutExpired:
            return "Test execution timed out"
        except Exception as e:
            return f"Error running tests: {str(e)}"


def validate_index(
    index: Index,
    config: Config,
    target: Optional[str] = None,
) -> ValidationResult:
    result = ValidationResult()
    store_validator = StorePathValidator()
    test_validator = TestValidator()
    current_system = get_current_system()

    # Parse target if provided
    target_pkg = None
    target_ver = None
    if target:
        parts = target.split("@")
        if len(parts) != 2:
            raise ValueError(f"Invalid target format: {target}. Use 'package@version'")
        target_pkg, target_ver = parts

    result.total_packages = len(index.pkgs)
    result.total_versions = sum(len(pkg.versions) for pkg in index.pkgs.values())

    for pkg_name, pkg_index in index.pkgs.items():
        if target_pkg and pkg_name != target_pkg:
            continue

        pkg_config = config.pkgs.get(pkg_name)
        if not pkg_config:
            logger.warning(f"Package {pkg_name} in index but not in config")
            continue

        for version_str, version_entry in pkg_index.versions.items():
            if target_ver and version_str != target_ver:
                continue

            result.validated_count += 1

            logger.info(f"Validating {pkg_name}@{version_str}")

            # Store path validation
            if version_entry.store_paths:
                for system, store_path in version_entry.store_paths.items():
                    logger.debug(f"  Checking store path for {system}: {store_path}")
                    if not store_validator.validate(store_path, system):
                        result.add_failure(
                            package=pkg_name,
                            version=version_str,
                            error="Store path validation failed",
                            store_path=store_path,
                            system=system,
                        )
            else:
                logger.debug(f"  No store paths to validate")

            # Config tests
            if pkg_config.tests:
                if not version_entry.store_paths:
                    result.add_failure(
                        package=pkg_name,
                        version=version_str,
                        error="No store paths available for testing",
                    )
                else:
                    for system, store_path in version_entry.store_paths.items():
                        if system != current_system:
                            # Only run store objects for the current system
                            continue
                        logger.debug(f"  Running tests for: {store_path}")
                        test_error = test_validator.validate(
                            version_str, pkg_config.tests, store_path
                        )
                        if test_error:
                            result.add_failure(
                                package=pkg_name,
                                version=version_str,
                                error=test_error,
                                system=system,
                            )
    if target and result.validated_count == 0:
        raise ValueError(f"No matching package/version found for target: {target}")

    return result


def format_validation_report(result: ValidationResult) -> str:
    """Format validation result as a human-readable report."""
    lines = [
        "=" * 60,
        "Validation Report",
        "=" * 60,
        f"Total packages: {result.total_packages}",
        f"Total versions: {result.total_versions}",
        f"Validated: {result.validated_count}",
        "",
    ]

    if result.has_failures():
        lines.append("FAILURES:")
        lines.append("-" * 60)
        for failure in result.failures:
            lines.append(f"{failure.package}@{failure.version}:")
            lines.append(f"  Error: {failure.error}")
            if failure.system:
                lines.append(f"  System: {failure.system}")
            if failure.store_path:
                lines.append(f"  Store path: {failure.store_path}")
            lines.append("")
        lines.append("=" * 60)
        lines.append(result.summary())
    else:
        lines.append("No validation failures detected!")
        lines.append("=" * 60)
        lines.append(result.summary())

    return "\n".join(lines)
