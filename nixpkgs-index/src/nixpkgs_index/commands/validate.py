"""Validate subcommand for checking index integrity."""

import click
import logging
import sys
from pathlib import Path
from typing import Optional

from ..config import Config
from ..index import Index
from ..validate import validate_index, format_validation_report
from .utils import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the config YAML file",
)
@click.option(
    "--index",
    type=click.Path(exists=True),
    required=True,
    help="Path to the index YAML file to validate",
)
@click.option(
    "--target",
    type=str,
    help="Target specific package and version (format: package@version, e.g. node@24.10.0)",
)
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
def validate(config: str, index: str, target: Optional[str], verbosity: int) -> None:
    """Validate index integrity and package correctness."""

    setup_logging(verbosity)

    logger.info("Loading configuration...")
    config_obj = Config.load(Path(config))

    logger.info("Loading index...")
    index_obj = Index.load(Path(index))
    total_versions = sum(len(pkg.versions) for pkg in index_obj.pkgs.values())
    logger.info(
        f"Index contains {len(index_obj.pkgs)} packages, {total_versions} versions"
    )

    if target:
        logger.info(f"Running validation for target: {target}")
    else:
        logger.info("Running full index validation...")

    logger.info("=" * 60)
    result = validate_index(index_obj, config_obj, target)
    logger.info("=" * 60)

    report = format_validation_report(result)
    print(report)

    if result.has_failures():
        sys.exit(1)
