# Mise nixpkgs plugin

A [mise](https://mise.jdx.dev/) backend plugin that installs pre-built development tools from [Nix](https://nixos.org/) and [nixpkgs](https://github.com/NixOS/nixpkgs). This bridges mise's developer experience with Nix's reproducible package ecosystem—you get exact versions and binary caching without needing to understand Nix expressions.

## Why this exists

Version managers typically rely on compiling tools from source or fetching pre-built binaries from language-specific sources. This plugin takes a different approach: it uses the nixpkgs ecosystem and its pre-built binary cache infrastructure (cache.nixos.org) to provide:

- **Exact version reproducibility**: Pin to specific package versions via nixpkgs commits
- **Pre-built binaries**: No compilation required, fetch from Nix binary caches
- **Broad platform support**: Works on Linux and macOS (both x86_64 and ARM64)
- **No nixpkgs evaluation at runtime**: Fast installs using a pre-generated index

Note: check out [limitations and tradeoffs](#limitations-and-tradeoffs) for important caveats.

## Installation

### Prerequisites

- [mise](https://mise.jdx.dev/) installed
- [Nix](https://nixos.org/download.html) installed on your system

### Install the plugin

First, install the plugin itself:

```bash
mise plugin install nixpkgs https://github.com/bitriseio/mise-nix-plugin
```

### Using the plugin

Now you can install tools via the nixpkgs backend:

```bash
# Install a specific version
mise use nixpkgs:ruby@3.3.8

# List available versions
mise ls-remote nixpkgs:ruby
```

## How it works

The plugin uses a pre-generated index file (`nixpkgs-index.json`) that maps package versions to specific nixpkgs commits and Nix store paths. When you request a version:

1. The plugin looks up the store path for that version
2. Runs `nix-store --realise` to fetch it from binary caches
3. Creates a symlink in mise's installation directory

This means no nixpkgs evaluation happens during installation—the plugin is fast and doesn't require fetching the nixpkgs repository. The index is maintained separately using the [`nixpkgs-index`](nixpkgs-index/) tool (see its README for details on how indexing works).

### Limitations and tradeoffs

#### Dynamic linking and Linux

Nix packages are built with a glibc version that is most likely higher than what is installed on most Linux distros. This can lead to runtime linking errors when using Nix-built binaries, especially when the tool compiles native code (e.g. Ruby gems with native extensions). You might work around this by overriding `$LD_LIBRARY_PATH`, but this affects all subprocesses and causes other crashes in those subprocesses.

Therefore, Linux support is experimental, use at your own risk.

macOS dynamic linking is slightly different (see `linked-on-or-later check` [here](https://developer.apple.com/forums/thread/715385)), so it doesn't have the above limitation.

#### Use of official Nix binary cache

This plugin relies on the official Nix binary cache (cache.nixos.org) to fetch pre-built binaries. While this cache is generally reliable and fast, this could be a supply-chain risk for you.

#### Older tool versions are frozen in time

The index maps specific tool versions to specific nixpkgs commits. While Nix guarantees reproducibility, older tool versions will not receive updates (e.g. security patches).

## Supported tools

Currently indexed and supported:

- **Ruby**
- **Python**
- **Node.js**

The index covers both `x86_64-linux` and `aarch64-darwin` (macOS Apple Silicon) architectures and is updated weekly via automated CI. To add more tools, open an issue or submit a PR updating [`nixpkgs-index-config.yml`](nixpkgs-index-config.yml).

## Configuration

This plugin works out of the box with no configuration. The bundled `nixpkgs-index.json` file includes mappings for all supported tools.

If you want to customize which packages are indexed or maintain your own index, see the [`nixpkgs-index`](nixpkgs-index/) tool documentation.

## Development

```bash
# Format Lua code
mise run format

# Run linting
mise run lint

# Run tests (requires Nix)
mise run test

# Run full CI suite
mise run ci
```

## Alternatives and prior art

- [mise-nix](https://github.com/chadac/mise-nix) - Alternative approach using Nix flakes
- [nixpkgs-python](https://github.com/cachix/nixpkgs-python) - Similar concept for Python versions specifically
- [Hermit](https://cashapp.github.io/hermit/) - Another tool version manager with Nix-like properties

## License

MIT
