"""Command-line interface for nixpkgs-index."""

import click

from .commands import index, validate


@click.group()
def cli() -> None:
    """Nixpkgs package indexing and validation tool."""
    pass


cli.add_command(index)
cli.add_command(validate)


if __name__ == "__main__":
    cli()
