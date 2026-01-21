local M = {}

function M.is_linux()
    return RUNTIME.osType == "linux"
end

function M.is_darwin()
    return RUNTIME.osType == "darwin"
end

-- Get a Nix store dependency path by pattern from a store path's references
-- Example: get_store_dependency("/nix/store/...-ruby-3.3.10", "glibc") returns "/nix/store/...-glibc-2.40-66"
function M.get_store_dependency(store_path, pattern)
    local cmd = require("cmd")
    local query_cmd = string.format(
        "nix-store --query --references %s 2>/dev/null | grep -E '%s' | head -1",
        store_path,
        pattern
    )
    local result = cmd.exec(query_cmd)
    -- Trim whitespace
    result = result:gsub("^%s*(.-)%s*$", "%1")
    if result == "" then
        return nil
    end
    return result
end

function M.current_system()
    local os = ""
    if RUNTIME.osType == "darwin" then
        os = "darwin"
    elseif RUNTIME.osType == "linux" then
        os = "linux"
    elseif RUNTIME.osType == "windows" then
        error("Windows is not supported by Nix")
    end

    local arch = ""
    if RUNTIME.archType == "amd64" then
        arch = "x86_64"
    elseif RUNTIME.archType == "arm64" then
        arch = "aarch64"
    else
        error("Unsupported architecture: " .. RUNTIME.archType)
    end

    return arch .. "-" .. os
end

return M
