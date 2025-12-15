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

    local runtime_deps = require("lib.runtime_deps")
    local runtime_dep_env_vars = runtime_deps.get_env_vars(install_path, tool, version, RUNTIME.osType)
    for _, env_var in ipairs(runtime_dep_env_vars) do
        table.insert(env_vars, env_var)
    end

    if tool == "ruby" then
        -- Nix store is read-only, gems should be installed to the state dir
        table.insert(env_vars, { key = "GEM_HOME", value = file.join_path(install_path, "state/gems") })
        table.insert(env_vars, { key = "GEM_PATH", value = file.join_path(install_path, "state/gems/gems") })
        table.insert(env_vars, { key = "PATH", value = file.join_path(install_path, "state/gems/bin") })
    elseif tool == "python" then
        -- TODO: env var inspiration: https://github.com/cashapp/hermit-packages/blob/master/python3.hcl#L6
        -- TODO: pkgs.python3 doesn't contain `pip`, and pkgs.python3Packages.pip doesn't expose the `python` bin
    end

    local man_path = file.join_path(install_path, "share", "man")
    table.insert(env_vars, { key = "MANPATH", value = man_path })

    return {
        env_vars = env_vars,
    }
end
