-- hooks/backend_install.lua
-- Installs a specific version of a tool
-- Documentation: https://mise.jdx.dev/backend-plugin-development.html#backendinstall

function PLUGIN:BackendInstall(ctx)
    local tool = ctx.tool
    local version = ctx.version
    local install_path = ctx.install_path

    -- Validate inputs
    if not tool or tool == "" then
        error("Tool name cannot be empty")
    end
    if not version or version == "" then
        error("Version cannot be empty")
    end
    if not install_path or install_path == "" then
        error("Install path cannot be empty")
    end

    -- nixpkgs mapping validation
    local nix = require("nix")
    local nixpkgs_mapping = require("nixpkgs_mapping")
    local mapping = nixpkgs_mapping.parse_mapping_file()
    local nix_system_string = nix.current_system()
    if
        not mapping.pkgs
        or not mapping.pkgs[tool]
        or not mapping.pkgs[tool][version]
        or not mapping.pkgs[tool][version].store_paths[nix_system_string]
    then
        error("No nixpkgs mapping found for " .. tool .. "@" .. version .. " on " .. nix_system_string)
    end

    local cmd = require("cmd")

    -- Create installation directory
    cmd.exec("mkdir -p " .. install_path)
    -- Create state dir (Nix store is read-only, the state dir is for things like Ruby gems, Cargo crates, etc.)
    cmd.exec("mkdir -p " .. install_path .. "/state")

    -- Nix invocation
    local nix_cmd_start = os.time()
    local store_object = mapping.pkgs[tool][version].store_paths[nix_system_string]
    -- Nix details:
    -- --add-root: registers a GC root for the store path.
    --             This prevents the store path from being GC'd when the user runs nix-collect-garbage.
    -- TODO: configurable behavior when store object is not available in binary cache: fail or build from source
    -- We could use os.getenv() here.
    local nix_cmd = "nix-store --realise " .. store_object .. " --add-root " .. install_path .. "/result"
    local output = cmd.exec(nix_cmd)
    print(output)
    if output:match("error") or output:match("failed") then
        error("Failed to install " .. tool .. "@" .. version .. ": " .. output)
    end
    print(string.format("Nix build took %ds", os.time() - nix_cmd_start))

    return {}
end
