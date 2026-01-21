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

    if tool == "ruby" then
        -- Nix store is read-only, gems should be installed to the state dir
        table.insert(env_vars, { key = "GEM_HOME", value = file.join_path(install_path, "state/gems") })
        table.insert(env_vars, { key = "GEM_PATH", value = file.join_path(install_path, "state/gems/gems") })
        table.insert(env_vars, { key = "PATH", value = file.join_path(install_path, "state/gems/bin") })

        -- On Linux, enable native gem compilation with host gcc and apt-installed dev libraries.
        -- This solves the glibc version mismatch issue where Nix Ruby requires glibc 2.38+
        -- but host systems (e.g., Ubuntu 22.04) have older glibc.
        local nix = require("lib.nix")
        if nix.is_linux() then
            local store_path = file.join_path(install_path, "result")
            local glibc_path = nix.get_store_dependency(store_path, "glibc")
            local gcc_lib_path = nix.get_store_dependency(store_path, "gcc.*lib")
            local ruby_lib_path = file.join_path(store_path, "lib")

            if glibc_path and gcc_lib_path then
                -- RUBYOPT: Load script that modifies RbConfig to add rpath flags for gem compilation
                local rubyopt_path = file.join_path(install_path, "state", "ldflags_inject.rb")
                table.insert(env_vars, { key = "RUBYOPT", value = "-r" .. rubyopt_path })

                -- CC: Use gcc wrapper that reorders -L flags to put Nix paths first
                -- This ensures the linker finds Nix glibc before system glibc during symbol resolution
                local gcc_wrapper_path = file.join_path(install_path, "state", "gcc-wrapper")
                table.insert(env_vars, { key = "CC", value = gcc_wrapper_path })

                -- PATH: Add wrapper bin directory FIRST so Ruby wrappers are used
                -- The wrappers set LD_LIBRARY_PATH only when invoking Ruby executables,
                -- avoiding glibc conflicts with system binaries like bash
                local wrapper_bin_path = file.join_path(install_path, "state", "bin")
                table.insert(env_vars, 1, { key = "PATH", value = wrapper_bin_path })
            end
        end
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
