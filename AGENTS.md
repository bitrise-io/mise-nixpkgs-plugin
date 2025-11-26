
## Project Overview

This is a [mise](https://mise.jdx.dev/) backend plugin that enables installing pre-built tools from Nix and nixpkgs. The plugin bridges mise's version management with Nix's reproducible package ecosystem.

### Core Components

1. **Mise Plugin (Lua)**: Located in `hooks/` and `lib/`, implements the mise backend plugin interface
2. **nixpkgs-index (Python)**: A CLI tool in `nixpkgs-index/` that indexes package versions across nixpkgs commits

### Architecture

The plugin works by:
1. Reading a pre-generated index file (`nixpkgs-index.json`) that maps package versions to nixpkgs commits and store paths
2. Using `nix-store --realise` to fetch pre-built packages from binary caches
3. Creating symlinks in mise's installation directory to the Nix store paths

The separation allows the plugin to be fast (no nixpkgs evaluation at runtime) while maintaining reproducibility through the indexed store paths.

## Development Commands

### Mise Plugin

```bash
# Format Lua code
mise run format

# Lint Lua and GitHub Actions
mise run lint

# Run plugin tests (requires Nix)
mise run test

# Run all CI checks
mise run ci
```

### nixpkgs-index Tool

The indexer is a separate Python project in `nixpkgs-index/`:

```bash
cd nixpkgs-index

# Run the indexer
uv run nixpkgs-index index --config ../nixpkgs-index-config.yml --output ../nixpkgs-index.json --step-interval 1d

# Validate the index
uv run nixpkgs-index validate --config ../nixpkgs-index-config.yml --index ../nixpkgs-index.json

# Run tests
uv run pytest
```

## Key Files and Their Roles

- `nixpkgs-index.json`: Pre-generated mapping of package versions to Nix store paths (do not edit manually)
- `nixpkgs-index-config.yml`: Configuration for which packages to index and from which nixpkgs attributes
- `hooks/backend_*.lua`: Mise backend plugin hooks that implement version listing, installation, and environment setup
- `lib/nixpkgs_mapping.lua`: Parses the index JSON file
- `lib/nix.lua`: Detects current Nix system (e.g., `x86_64-linux`, `aarch64-darwin`)


## CI/CD

The project uses Bitrise for CI (see `bitrise.yml`):
- Runs linting and tests on every PR
- Validates the nixpkgs index on both macOS and Linux
- Has a scheduled workflow that updates the index weekly and creates a PR

## Important Notes

- The plugin requires Nix to be installed on the system
- Store paths are platform-specific (recorded for `x86_64-linux` and `aarch64-darwin`)
- The index update process can take hours due to the need to evaluate nixpkgs at many historical commits
- When adding new packages, update `nixpkgs-index-config.yml` and regenerate the index
