-- hooks/backend_list_versions.lua
-- Lists available versions for a tool in this backend
-- Documentation: https://mise.jdx.dev/backend-plugin-development.html#backendlistversions

function PLUGIN:BackendListVersions(ctx)
    local tool = ctx.tool

    -- Validate tool name
    if not tool or tool == "" then
        error("Tool name cannot be empty")
    end

    local nix = require("nix")
    local nixpkgs_mapping = require("nixpkgs_mapping")
    local mapping = nixpkgs_mapping.parse_mapping_file()

    local packages = mapping.pkgs or {}
    if not packages[tool] then
        error("Tool " .. tool .. " not found in mapping")
    end

    local versions = {}
    local nix_system_string = nix.current_system()
    for version, nix_data in pairs(packages[tool]) do
        if nix_data.store_paths[nix_system_string] then
            table.insert(versions, version)
        end
    end

    if #versions == 0 then
        error("No versions found for " .. tool)
    end

    return { versions = versions }
end
