# nixpkgs-index

A CLI tool that indexes package versions across nixpkgs commits, mapping exact package versions to their nixpkgs commit hashes. This enables reproducible package installations across the nixpkgs rolling release model.

## Why nixpkgs-index?

Nixpkgs follows a rolling release model where attributes (packages) contain different versions over time. For example, `ruby_3_4` is version 3.4.7 today, but will be upgraded to 3.4.8 and newer. To install exact package versions reproducibly, you need to know which nixpkgs commit contained a specific version.

This tool automates building and maintaining an index that maps exact versions to nixpkgs commit hashes, enabling tools like [mise](https://mise.jdx.dev/) to fetch reproducible package versions.

You get this structured data as output:
```yaml
pkgs:
  ruby:
    "3.4.7":
      nixpkgs_commit: c8aa8cc00a5cb57fada0851a038d35c08a36a2bb
      commit_timestamp: 2024-06-10T12:34:56Z
    "3.3.9":
      nixpkgs_commit: 3d3d9516f4c2367c00bf6968f8f93c62c555c03c
      commit_timestamp: 2024-06-09T12:34:56Z
    "3.3.8":
      nixpkgs_commit: abc123def456789...
      commit_timestamp: 2024-06-08T10:00:00Z
      store_paths:  # Optional, only when record_store_paths is enabled
        x86_64-linux: /nix/store/abc123...-ruby-3.3.8
        aarch64-darwin: /nix/store/def456...-ruby-3.3.8
```

Now you can instantly fetch Ruby 3.3.8 by pointing nixpkgs to commit `abc123def456789...`, or optionally fetch it directly from a binary cache using the store path.

## Getting Started

### Prerequisites

- Python 3.10+ and `uv`
- `nix` command-line tool (for evaluating nixpkgs attributes)
- GitHub personal access token (recommended for API rate limits)

### Quick Start

1. **Clone or navigate to the project repo**:
   ```bash
   cd nixpkgs-index
   ```

2. **Set up your GitHub token** (optional but recommended):
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   ```
   Or create a `.env` file in the repo root:
   ```
   GITHUB_TOKEN=your_github_token_here
   ```

3. **Create a configuration file** (e.g., `config.yml`):
  ```yaml
  # Which nixpkgs branch to use
  # Use stable channel branches (nixpkgs-unstable, nixpkgs-25.05, etc.)
  # Avoid master branch - it may not be fully built and cached
  branch: nixpkgs-unstable

  pkgs:
    # Package ID (user-friendly name for your use case)
    ruby:
      # List of nixpkgs attributes to evaluate and extract versions from
      # It's a good idea to include multiple version-specific attributes to capture all versions over time.
      # For example, when "ruby" was at 3.2.x, "ruby_3_1" might have been at 3.1.7
      # - evaluating only "ruby" would miss 3.1.{4,5,6,7} from that time period
      nixpkgs_attributes:
        - ruby
        - ruby_3_4
        - ruby_3_3
        - ruby_3_2
        - ruby_3_1

    python:
      # Another package with its own version branches
      nixpkgs_attributes:
        - python3
        - python313
        - python312
        - python311
        - python310

  # Optional: Record store paths for each system
  # This allows fetching packages directly from a binary cache without re-evaluating nixpkgs
  eval:
    record_store_paths: true
    systems:
      - x86_64-linux
      - aarch64-darwin
  ```

4. **Run the indexer**:
   ```bash
   uv run nixpkgs-index --config config.yml --output index.yml --step-interval 1d
   ```

The tool will discover commits at the specified intervals, evaluate your configured packages, and generate an index YAML file mapping versions to commit hashes.

## Usage


### Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--config PATH` | Yes | - | Path to configuration YAML file |
| `--output PATH` | Yes | `nixpkgs-index.yaml` | Path to output index YAML file |
| `--nixpkgs-path PATH` | No | `.nixpkgs-checkout` | Path for nixpkgs repository (auto-initialized) |
| `--since DATETIME` | No | - | Start indexing from this ISO 8601 date (e.g., `2025-01-01T00:00:00Z`) |
| `--until DATETIME` | No | HEAD | Stop indexing at this ISO 8601 date |
| `--step-interval INTERVAL` | No | `1d` | Time interval between evaluations (`1h`, `6h`, `12h`, `1d`, `7d`, `30d`) |
| `--max-steps N` | No | - | Maximum number of commits to evaluate |
| `-v, --verbose` | No | - | Increase verbosity (-v for INFO, -vv for DEBUG) |

### Examples

**Index the last 30 days at 1-day intervals:**
```bash
uv run nixpkgs-index --config config.yml --output index.yml \
  --since 2025-09-26T00:00:00Z --step-interval 1d
```

**Index the last 100 commits only:**
```bash
uv run nixpkgs-index --config config.yml --output index.yml --max-steps 100
```

**Use larger intervals for faster indexing:**
```bash
uv run nixpkgs-index --config config.yml --output index.yml --step-interval 7d
```

## How It Works

### Algorithm Overview

1. **Discover commits**: Use GitHub API to find commits at regular time intervals
2. **Fetch commits**: Shallow-clone specific commits into a local nixpkgs checkout
3. **Evaluate attributes**: Run `nix eval` to get package versions from each commit
4. **Update index**: Merge new versions into the index, keeping the newest commit for each version

### Detailed Process

#### Commit Discovery

The tool uses the GitHub Commits API to discover evenly-spaced commits across time:

- Endpoint: `GET /repos/NixOS/nixpkgs/commits`
- For each time interval going backwards:
  - Calculate target window: `(current_time - step_interval, current_time)`
  - Query: `GET /commits?since=<window_start>&until=<window_end>&per_page=1`
  - Take the oldest commit from that window

#### Repository Management

- Creates a sparse-checkout of nixpkgs (only `pkgs` and `lib` directories)
- Uses `git fetch --depth 1 origin <sha>` for efficient checkouts for each commit

#### Attribute Evaluation

For each commit, the tool runs:
```bash
nix eval --file . --raw ATTRIBUTE.version
```

This extracts the version number from each configured nixpkgs attribute.

#### Index Updates

Two main cases:

1. **New version**: Version not yet in index → add it
2. **Existing version**: Already in index → update commit only if current checkout is newer (based on timestamp)

The index keeps only one entry per version, updated to the newest commit timestamp.

#### Error Handling

- If evaluation fails for a specific attribute: log warning, continue
- If all attributes fail for a commit: log warning, continue
- Individual failures don't abort the entire indexing process

## Development


### Running Tests

```bash
uv run pytest
```

### TODO and Future Work

- [x] Evaluate store objects and store them per-system in the index
- [x] Optimize the commit update by comparing the old vs. new store objects and only update the commit hash if the store object changed (if not, nothing relevant changed for that package/version)
- [ ] Split the index file per package for easier diffs
- [x] Catch known Nix eval errors like attribute is EOL and throws error on purpose
- [ ] Use nix-eval-jobs for parallel evaluation of multiple attributes
- [ ] Mise Python tooling


## Troubleshooting

### "Failed to evaluate attribute"

**Causes:**
- Attribute doesn't exist in older nixpkgs commits
- Nix evaluation errors
- Package definition issues

**Solution:** This is non-fatal. The tool logs a warning and continues. Verify your attribute names in older nixpkgs versions.

### GitHub API rate limit exceeded

**Solution:**
- Set `GITHUB_TOKEN` environment variable with a personal access token
- This increases your rate limit from 60 to 5,000 requests/hour
- Create a token at https://github.com/settings/tokens (needs `public_repo` scope)

