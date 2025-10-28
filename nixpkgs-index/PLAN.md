# nixpkgs-index

I want to create an index of package versions and the precise nixpkgs commit hash where a given package version is available. As nixpkgs follows the rolling release model, a nixpkgs attribute (package) contains different versions of the package over time. For example, the nixpkgs attribute `ruby_3_4` is version 3.4.7 today, but it's going to be upgraded to 3.4.8 and newer 3.4.x versions. Yet, me and my users need to install exact versions of packages, therefore we need an index that maps from an exact version to a nixpkgs commit hash where the given attribute (e.g. `ruby_3_4` or `python3`) contains the exact version.

### Design and architecture

Create a simple CLI tool that automates the building and maintenance of this index. This tool is going to be an internal utility, so keep it simple, there is no need to make it overly complex and resilient.

The CLI tool should have a declarative config file for what nixpkgs attributes to index:

```yml
# Which branch of nixpkgs to use. This is important because the tip of the master branch might be uncached and we are only interested in Nix store entries that are already present in the binary cache. The nixpkgs-unstable (and other channel branches) are only advanced once Hydra has built and cached the packages.
branch: nixpkgs-unstable

pkgs:
  # Human-friendly package ID, this is independent of the precise nixpkgs attribute
  ruby:
    # nixpkgs attributes to evaluate and read version numbers from.
    # Note: we need to try multiple attributes because the "versioned" attributes might be more recent than the time when the "unversioned" attribute pointed to a given version
    # in the past. For example:
    # - `ruby` is 3.3.9 at the moment
    # - `ruby_3_1` is 3.1.7 at the moment
    # - The last time `ruby` was 3.1.x, it was at version 3.1.3. We would miss 3.1.{4,5,6,7} if we were only evaluaating the `ruby` attribute
    nixpkgs_attributes:
    - ruby
    - ruby_3_4
    - ruby_3_3
    - ruby_3_2
    - ruby_3_1

# Evaluation settings
eval:
  # Besides the nixpkgs commit hash, also record the Nix store paths for each system defined below.
  # This is useful for fetching store objects from a binary cache directly without needing to evaluate nixpkgs again. 
  record_store_paths: true
  systems:
  - x86_64-linux
  - aarch64-darwin
```

The output is an index, which is another YML file for simplicity:

```yml
pkgs:
  ruby:
    # Key: version detected from evaluation
    # Value: nixpkgs commit SHA and timestamp of commit
    "3.3.9":
        nixpkgs_commit: c8aa8cc00a5cb57fada0851a038d35c08a36a2bb
        commit_timestamp: 2024-06-10T12:34:56Z
    "3.3.8":
        nixpkgs_commit: 3d3d9516f4c2367c00bf6968f8f93c62c555c03c
        commit_timestamp: 2024-06-09T12:34:56Z
```

Tech stack: Python, Click, uv and standard pyproject.toml

### The algorithm

The basic idea:
1. Use GitHub API to discover commits at time intervals
2. For each discovered commit SHA, fetch it shallowly into the local nixpkgs checkout
3. Evaluate the nixpkgs attributes in the checkout and read the version numbers
4. Update the index file with the new data
5. Move back in time by the step interval and repeat until we reach the configured limit

### Optional: record store paths

If `eval.record_store_paths` is enabled in the config, the tool will also evaluate and record the Nix store paths for each system defined in the config file. This allows users to fetch the exact store objects from a binary cache without needing to have a nixpkgs checkout and evaluate Nix attributes again.

### Implementation details

#### nixpkgs checkout

- Create a working directory for the nixpkgs checkout (relative to this repo) and gitignore it
- Initialize as a git repo with sparse-checkout configured for `pkgs` and `lib` directories only (root files are included automatically)
- Use `git fetch --depth 1 origin <sha>` to fetch specific commits as needed
- This avoids the unreliable `--shallow-since` and `--deepen` operations that fail with large repos like nixpkgs

#### Discovering commits via GitHub API

Use the GitHub Commits API to discover which commits to evaluate:
- Endpoint: `GET /repos/NixOS/nixpkgs/commits`
- Parameters: `sha=<branch>`, `since=<datetime>`, `until=<datetime>`, `per_page=100`
- Authenticated requests have a rate limit of 5,000 requests/hour
- The API returns commit SHA and timestamp, which is all we need

Algorithm for discovering commits:
1. Start with the most recent commit (HEAD of the configured branch)
2. For each time interval going backwards:
   - Calculate target time window: `(current_time - step_interval, current_time)`
   - Query API: `GET /commits?since=<window_start>&until=<window_end>&per_page=1`
   - Take the oldest commit from that window (if any)
   - This gives us evenly-spaced commits across time
3. Continue until we reach the `--since` date or `--max-steps` limit

#### Evaluating nixpkgs attributes

Once a commit is checked out, run `nix eval --file . --raw ruby_3_5.version` to get the version of the `ruby_3_5` attribute.

If `eval.record_store_paths` is enabled, also run `nix eval --file . --raw <attribute> --system <system>` (the main attribute, not `.version`) for each system defined in the config. The nix store paths should be recorded alongside the commit SHA and timestamp in the index, like this:

```yml
pkgs:
  ruby:
    "3.3.9":
        nixpkgs_commit: c8aa8cc00a5cb57fada0851a038d35c08a36a2bb
        commit_timestamp: ...
        store_paths:
          x86_64-linux: /nix/store/...
          aarch64-darwin: /nix/store/...
```

#### Updating the index file

There are two main cases here:
1. The version number is not present in the index for the given package: add it
2. The version number is already present: update the commit SHA and timestamp, but only if the current checkout is newer (based on the commit timestamp) than the one already in the index. Do not keep multiple entries for the same version, just update the existing one.

#### Configuration options

The CLI should have flags for configuring history traversal:
- `--since <datetime>`: Start indexing from this date going forward (ISO 8601 format, e.g. 2025-01-01T00:00:00Z). Default: go back as far as needed
- `--until <datetime>`: Stop indexing at this date (ISO 8601 format). Default: HEAD (current time)
- `--step-interval <duration>`: Time interval between commit evaluations (e.g. 1h, 6h, 12h, 1d, 7d, 30d). Default: 1d
- `--max-steps <n>`: Maximum number of commits to evaluate (default: no limit)
- `--github-token <token>`: GitHub personal access token for API requests (can also be set via GITHUB_TOKEN env var)

Example: `--since 2025-01-01T00:00:00Z --step-interval 1d` will evaluate approximately one commit per day starting from January 1st, 2025.

#### Error handling

- If evaluation fails for any nixpkgs attribute (e.g., attribute doesn't exist in older commits, nix eval errors), log a warning and continue with the next attribute
- If all attributes fail for a commit, log a warning and continue with the next commit
- Do not abort the entire indexing process due to individual failures

