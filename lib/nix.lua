local M = {}

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
