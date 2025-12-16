local M = {}

-- The main Nix package has runtime deps (other Nix store objects), which provide the usual
-- C headers, shared libraries and pkgconfig files. This function queries those runtime deps
-- and constructs the necessary env vars to make those dependencies available at runtime.
-- In practice, this is important when running package manager binaries that try to build native code
-- (e.g. Ruby gems that compile C extensions).
function M.get_env_vars(install_path, tool, version, os_type)
    local file = require("file")
    local cmd = require("cmd")

    local result_path = file.join_path(install_path, "result")
    local requisites = cmd.exec("nix-store --query --requisites " .. result_path)

    if requisites:match("error") or requisites:match("failed") then
        error("Failed to query runtime deps for " .. tool .. "@" .. version .. ": " .. requisites)
    end

    local store_paths = {}
    for store_path in string.gmatch(requisites, "[^%s]+") do -- poor man's strings.Split(requisites, "\n")
        table.insert(store_paths, store_path)
    end

    local lib_paths = M.find_lib_paths(store_paths, file, cmd)
    local pkgconfig_paths = M.find_pkgconfig_paths(store_paths, file, cmd)

    local env_vars = {}
    local lib_env_vars = M.create_library_env_vars(lib_paths, os_type)
    local pkgconfig_env_vars = M.create_pkgconfig_env_vars(pkgconfig_paths)

    for _, var in ipairs(lib_env_vars) do
        table.insert(env_vars, var)
    end
    for _, var in ipairs(pkgconfig_env_vars) do
        table.insert(env_vars, var)
    end

    return env_vars
end

-- TODO: file.exists() doesn't exist 🤷
-- https://github.com/jdx/mise/pull/6754
-- Can be replaced once our pinned mise version is bumped again
function M.dir_exists(path, cmd_module)
    local check_cmd = "if [ -d " .. path .. " ]; then echo 'exists'; fi"
    local check_output = cmd_module.exec(check_cmd)
    return check_output:match("exists") ~= nil
end

-- Finds all lib directories in the given store paths
function M.find_lib_paths(store_paths, file_module, cmd_module)
    local lib_paths = {}
    for _, store_path in ipairs(store_paths) do
        local lib_path = file_module.join_path(store_path, "lib")
        if M.dir_exists(lib_path, cmd_module) then
            table.insert(lib_paths, lib_path)
        end
    end
    return lib_paths
end

-- Finds all lib/pkgconfig directories in the given store paths
function M.find_pkgconfig_paths(store_paths, file_module, cmd_module)
    local pkgconfig_paths = {}
    for _, store_path in ipairs(store_paths) do
        local pkgconfig_path = file_module.join_path(store_path, "lib/pkgconfig")
        if M.dir_exists(pkgconfig_path, cmd_module) then
            table.insert(pkgconfig_paths, pkgconfig_path)
        end
    end
    return pkgconfig_paths
end

-- Exposes shared library paths for the (platform-specific) dynamic linker
function M.create_library_env_vars(lib_paths, os_type)
    local env_vars = {}
    local key = nil

    if os_type == "linux" then
        key = "LD_LIBRARY_PATH"
    elseif os_type == "darwin" then
        key = "DYLD_LIBRARY_PATH"
    else
        error("Unsupported architecture: " .. os_type)
    end

    for _, lib_path in ipairs(lib_paths) do
		if not lib_path:match("glibc") then
			table.insert(env_vars, { key = key, value = lib_path })
		end
    end

    return env_vars
end

function M.create_pkgconfig_env_vars(pkgconfig_paths)
    local env_vars = {}
    for _, pkgconfig_path in ipairs(pkgconfig_paths) do
        table.insert(env_vars, { key = "PKG_CONFIG_PATH", value = pkgconfig_path })
    end
    return env_vars
end

return M
