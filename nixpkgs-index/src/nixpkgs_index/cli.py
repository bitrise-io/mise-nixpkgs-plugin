"""Command-line interface for nixpkgs-index."""

import click
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import colorlog
from dotenv import load_dotenv

from .config import Config
from .index import Index
from .nixpkgs import NixpkgsRepo
from .github import GitHubClient

logger = logging.getLogger(__name__)


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level."""
    if verbosity >= 1:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Create console handler with color formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Use colorlog for automatic color support
    formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    handler.setFormatter(formatter)

    # Clear existing handlers and add new one
    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def parse_interval(interval_str: str) -> timedelta:
    """Parse interval strings like '1h', '6h', '1d', '7d', '30d'."""
    if not interval_str:
        raise ValueError("Interval string cannot be empty")

    unit = interval_str[-1]
    try:
        amount = int(interval_str[:-1])
    except ValueError:
        raise ValueError(f"Invalid interval format: {interval_str}")

    if unit == "h":
        return timedelta(hours=amount)
    elif unit == "d":
        return timedelta(days=amount)
    else:
        raise ValueError(
            f"Unknown interval unit: {unit}. Supported units: h (hours), d (days)"
        )


@click.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the config YAML file",
)
@click.option(
    "--output",
    type=click.Path(),
    required=True,
    default="nixpkgs-index.yaml",
    help="Path to the output index YAML file",
)
@click.option(
    "--nixpkgs-path",
    type=click.Path(),
    default=".nixpkgs-checkout",
    help="Path to clone/use for nixpkgs repository",
)
@click.option(
    "--since",
    type=str,
    help="Start indexing from this date (ISO 8601 format, e.g. 2025-01-01T00:00:00Z)",
)
@click.option(
    "--until",
    type=str,
    help="Stop indexing at this date (ISO 8601 format, default: HEAD/current time)",
)
@click.option(
    "--step-interval",
    type=str,
    default="1d",
    help="Time interval between evaluations (e.g. 1h, 6h, 12h, 1d, 7d, 30d)",
)
@click.option("--max-steps", type=int, help="Maximum number of commits to evaluate")
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
def main(
    config: str,
    output: str,
    nixpkgs_path: str,
    since: Optional[str],
    until: Optional[str],
    step_interval: str,
    max_steps: Optional[int],
    verbosity: int,
) -> None:
    """Index package versions across nixpkgs commits."""

    setup_logging(verbosity)

    # Load environment variables from .env file if present
    load_dotenv()

    # Load configuration
    config_obj = Config.load(Path(config))
    logger.info(f"Loaded config for branch: {config_obj.branch}")
    logger.info(f"Packages to index: {list(config_obj.pkgs.keys())}")
    for pkg_name, pkg_config in config_obj.pkgs.items():
        logger.debug(f"  {pkg_name}: {pkg_config.nixpkgs_attributes}")

    # Parse step interval
    try:
        interval = parse_interval(step_interval)
        logger.info(f"Using step interval: {step_interval} ({interval})")
    except ValueError as e:
        raise click.UsageError(str(e))

    # Parse date parameters
    since_dt = None
    until_dt = None

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            logger.info(f"Indexing since: {since_dt.isoformat()}")
        except ValueError:
            raise click.UsageError(f"Invalid --since date format: {since}")

    if until:
        try:
            until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
            logger.info(f"Indexing until: {until_dt.isoformat()}")
        except ValueError:
            raise click.UsageError(f"Invalid --until date format: {until}")

    # Get GitHub token from environment
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning("No GitHub token found in GITHUB_TOKEN environment variable.")
        logger.warning("API rate limits will be very restrictive (60 requests/hour).")
        logger.warning(
            "Set GITHUB_TOKEN in environment or .env file for authenticated access (5000 requests/hour)."
        )

    # Initialize GitHub API client
    github_client = GitHubClient(token)
    remaining, limit = github_client.check_rate_limit()
    logger.info(f"GitHub API rate limit: {remaining}/{limit} requests remaining")

    # Discover commits to evaluate using GitHub API
    logger.info("=" * 50)
    logger.info("Discovering commits via GitHub API...")
    logger.info("=" * 50)

    commits = github_client.discover_commits_at_intervals(
        branch=config_obj.branch,
        step_interval=interval,
        since=since_dt,
        until=until_dt,
        max_steps=max_steps,
    )

    if not commits:
        logger.error("No commits discovered to evaluate!")
        return

    logger.info("=" * 50)
    logger.info(f"Will evaluate {len(commits)} commits")
    logger.info(
        f"Date range: {commits[0].timestamp.isoformat()} to {commits[-1].timestamp.isoformat()}"
    )
    logger.info("=" * 50)

    # Initialize nixpkgs repository
    repo_path = Path(nixpkgs_path).resolve()
    logger.info(f"Using nixpkgs repository at: {repo_path}")
    repo = NixpkgsRepo(repo_path, config_obj.branch)
    repo.ensure_initialized()

    # Load or create index
    output_path = Path(output).resolve()
    index = Index.load(output_path)
    logger.info(
        f"Starting index state: {sum(len(pkg.versions) for pkg in index.pkgs.values())} total versions"
    )
    for pkg_name, pkg_index in index.pkgs.items():
        logger.debug(f"  {pkg_name}: {len(pkg_index.versions)} versions")

    # Evaluate each commit
    logger.info("=" * 50)
    logger.info("Starting evaluation...")
    logger.info("=" * 50)

    total_updates = 0

    for i, commit in enumerate(commits, 1):
        logger.info(
            f"[{i}/{len(commits)}] Evaluating commit {commit.sha[:12]} ({commit.timestamp.isoformat()})"
        )

        try:
            repo.fetch_and_checkout_commit(commit.sha)
        except Exception as e:
            logger.error(f"Failed to fetch/checkout commit: {e}")
            continue

        commit_updates = 0

        for pkg_name, pkg_config in config_obj.pkgs.items():
            for attribute in pkg_config.nixpkgs_attributes:
                version = repo.evaluate_attribute(attribute)

                if version:
                    store_paths = None
                    if config_obj.eval.record_store_paths:
                        store_paths = {}
                        for system in config_obj.eval.systems:
                            store_path = repo.evaluate_attribute_store_path(
                                attribute, system
                            )
                            if store_path:
                                store_paths[system] = store_path
                            else:
                                logger.warning(
                                    f"Failed to get store path for {attribute} on {system}"
                                )

                    updated = index.update_version(
                        pkg_name,
                        version,
                        commit.sha,
                        commit.timestamp.isoformat(),
                        store_paths,
                    )

                    if updated:
                        logger.info(f"  [{pkg_name}] {attribute}={version} (NEW)")
                        commit_updates += 1
                        total_updates += 1
                    else:
                        logger.debug(f"  [{pkg_name}] {attribute}={version} (skipped)")
                else:
                    logger.debug(f"  [{pkg_name}] {attribute}=<failed to evaluate>")

        index.save(output_path)
        total_versions = sum(len(pkg.versions) for pkg in index.pkgs.values())
        logger.info(
            f"Commit complete: {commit_updates} new versions, total index: {total_versions}"
        )

    logger.info("=" * 50)
    logger.info(f"Indexing complete!")
    logger.info(f"Total commits evaluated: {len(commits)}")
    logger.info(f"Total version updates: {total_updates}")
    total_versions = sum(len(pkg.versions) for pkg in index.pkgs.values())
    logger.info(f"Final index state: {total_versions} total versions")
    logger.info(f"Index saved to: {output_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
