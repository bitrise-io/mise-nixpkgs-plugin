-- hooks/backend_exec_env.lua
-- Sets up environment variables for a tool
-- Documentation: https://mise.jdx.dev/backend-plugin-development.html#backendexecenv

function PLUGIN:BackendExecEnv(ctx)
    local install_path = ctx.install_path
    local tool = ctx.tool
    local version = ctx.version

    local file = require("file")
    local bin_path = file.join_path(install_path, "result", "bin")

    local env_vars = {
        { key = "PATH", value = bin_path },
    }

    -- TODO: reimplement backend-specific env vars based on tool type (Python, Go, etc.)

    if tool == "ruby" then
        -- Nix store is read-only, gems should be installed to the state dir
        table.insert(env_vars, { key = "GEM_HOME", value = file.join_path(install_path, "state/gems") })
        table.insert(env_vars, { key = "GEM_PATH", value = file.join_path(install_path, "state/gems/gems") })
        table.insert(env_vars, { key = "PATH", value = file.join_path(install_path, "state/gems/bin") })
    elseif tool == "python" then
        -- TODO: pkgs.python3 doesn't contain `pip`, and pkgs.python3Packages.pip doesn't expose the `python` bin
        -- TODO: https://github.com/cashapp/hermit-packages/blob/master/python3.hcl#L6
    end

    -- Example: Backend-specific paths (like node_modules for npm)
    --[[
    -- For npm-like backends that install to subdirectories
    local modules_bin = file.join_path(install_path, "node_modules", ".bin")
    table.insert(env_vars, {key = "PATH", value = modules_bin})

    -- For Python-like backends with site-packages
    local site_packages = file.join_path(install_path, "lib", "python3.x", "site-packages")
    table.insert(env_vars, {key = "PYTHONPATH", value = site_packages})

    -- For Rust-like backends with cargo binaries
    local cargo_bin = file.join_path(install_path, ".cargo", "bin")
    table.insert(env_vars, {key = "PATH", value = cargo_bin})
    --]]

    -- Example: Library paths for compiled tools
    --[[
    local lib_path = file.join_path(install_path, "lib")
    local lib64_path = file.join_path(install_path, "lib64")

    if RUNTIME.osType == "Linux" then
        table.insert(env_vars, {key = "LD_LIBRARY_PATH", value = lib_path})
        table.insert(env_vars, {key = "LD_LIBRARY_PATH", value = lib64_path})
    elseif RUNTIME.osType == "Darwin" then
        table.insert(env_vars, {key = "DYLD_LIBRARY_PATH", value = lib_path})
    end
    --]]

    -- Example: Include paths for development tools
    --[[
    local include_path = file.join_path(install_path, "include")
    table.insert(env_vars, {key = "C_INCLUDE_PATH", value = include_path})
    table.insert(env_vars, {key = "CPLUS_INCLUDE_PATH", value = include_path})
    --]]

    local man_path = file.join_path(install_path, "share", "man")
    table.insert(env_vars, { key = "MANPATH", value = man_path })

    return {
        env_vars = env_vars,
    }
end
