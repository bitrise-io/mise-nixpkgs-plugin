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
    local nix = require("lib.nix")
    local nixpkgs_mapping = require("lib.nixpkgs_mapping")
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

    -- On Linux, create helper files for native gem compilation
    -- These solve the glibc version mismatch issue where Nix Ruby requires glibc 2.38+
    -- but host systems (e.g., Ubuntu 22.04) have older glibc.
    if tool == "ruby" and nix.is_linux() then
        local file = require("file")
        local store_path = file.join_path(install_path, "result")
        local glibc_path = nix.get_store_dependency(store_path, "glibc")
        local gcc_lib_path = nix.get_store_dependency(store_path, "gcc.*lib")
        local ruby_lib_path = file.join_path(store_path, "lib")

        if glibc_path and gcc_lib_path then
            -- Detect architecture for dynamic linker path
            local arch = nix.current_system():match("^([^-]+)")
            local ld_linux_name = arch == "aarch64" and "ld-linux-aarch64.so.1" or "ld-linux-x86-64.so.2"

            -- Create RUBYOPT injection script
            -- This modifies RbConfig to add rpath and dynamic linker flags for gem compilation
            local rubyopt_script = string.format([[
# Nix glibc compatibility for native gem compilation
nix_glibc = '%s'
nix_gcc_lib = '%s'
nix_ruby_lib = '%s'
nix_ld = "#{nix_glibc}/lib/%s"

system_lib_paths = [
  '/usr/lib/%s-linux-gnu',
  '/lib/%s-linux-gnu',
  '/usr/lib',
  '/lib'
].select { |p| Dir.exist?(p) }

extra_ldflags = [
  "-Wl,-rpath,#{nix_ruby_lib}",
  "-Wl,-rpath,#{nix_glibc}/lib",
  "-Wl,-rpath,#{nix_gcc_lib}/lib",
  system_lib_paths.map { |p| "-Wl,-rpath,#{p}" },
  "-Wl,--dynamic-linker=#{nix_ld}"
].flatten.join(' ')

require 'rbconfig'
RbConfig::MAKEFILE_CONFIG['LDFLAGS'] = "#{RbConfig::MAKEFILE_CONFIG['LDFLAGS']} #{extra_ldflags}"
RbConfig::CONFIG['LDFLAGS'] = "#{RbConfig::CONFIG['LDFLAGS']} #{extra_ldflags}"
]], glibc_path, gcc_lib_path, ruby_lib_path, ld_linux_name, arch, arch)

            local rubyopt_path = file.join_path(install_path, "state", "ldflags_inject.rb")
            -- Write Ruby script using heredoc
            local write_rubyopt_cmd = string.format([[cat > '%s' << 'RUBYEOF'
%s
RUBYEOF]], rubyopt_path, rubyopt_script)
            cmd.exec(write_rubyopt_cmd)

            -- Create gcc wrapper script
            -- This reorders -L flags to put Nix library paths first, ensuring correct glibc is found
            local gcc_wrapper_path = file.join_path(install_path, "state", "gcc-wrapper")
            -- Use [=[...]=] to avoid conflict with bash [[ ]]
            local write_gcc_wrapper_cmd = string.format([=[cat > '%s' << 'GCCEOF'
#!/bin/bash
# Nix glibc compatibility wrapper for gcc
# Reorders -L flags to put Nix paths first

NIX_GLIBC='%s'
NIX_GCC_LIB='%s'

NIX_L_FLAGS=""
OTHER_L_FLAGS=""
NON_L_ARGS=()

for arg in "$@"; do
    if [[ "$arg" == -L* ]]; then
        path="${arg#-L}"
        if [[ "$path" == /nix/store/* ]]; then
            NIX_L_FLAGS="$NIX_L_FLAGS $arg"
        else
            OTHER_L_FLAGS="$OTHER_L_FLAGS $arg"
        fi
    else
        NON_L_ARGS+=("$arg")
    fi
done

ALL_L_FLAGS="-L${NIX_GLIBC}/lib -L${NIX_GCC_LIB}/lib ${NIX_L_FLAGS} ${OTHER_L_FLAGS}"
exec /usr/bin/gcc ${ALL_L_FLAGS} "${NON_L_ARGS[@]}"
GCCEOF
chmod +x '%s']=], gcc_wrapper_path, glibc_path, gcc_lib_path, gcc_wrapper_path)
            cmd.exec(write_gcc_wrapper_cmd)

            -- Create wrapper bin directory with Ruby executable wrappers
            -- These wrappers set LD_LIBRARY_PATH only when invoking Ruby,
            -- avoiding glibc conflicts with system binaries like bash
            local wrapper_bin_dir = file.join_path(install_path, "state", "bin")
            cmd.exec("mkdir -p " .. wrapper_bin_dir)

            local real_bin_dir = file.join_path(install_path, "result", "bin")

            -- Get all Nix store dependencies with lib directories
            -- This includes openssl, zlib, libffi, libyaml, etc.
            local get_nix_libs_cmd = string.format(
                "nix-store --query --references %s 2>/dev/null | while read dep; do [ -d \"$dep/lib\" ] && echo -n \"$dep/lib:\"; done",
                store_path
            )
            local nix_lib_paths = cmd.exec(get_nix_libs_cmd):gsub(":$", "")

            local ld_library_path = string.format(
                "%s:%s:/lib/%s-linux-gnu:/usr/lib/%s-linux-gnu:/lib:/usr/lib",
                nix_lib_paths,
                ruby_lib_path,
                arch,
                arch
            )

            -- Create wrappers for Ruby executables
            -- Runtime executables (ruby, irb) need LD_LIBRARY_PATH for loading gems with native extensions
            -- Compilation executables (gem, bundle) should NOT set LD_LIBRARY_PATH to avoid
            -- breaking system tools (perl, etc.) that are called during gem installation
            local runtime_executables = { "ruby", "irb", "erb" }
            local compile_executables = { "gem", "bundle", "bundler", "rake", "rdoc", "ri" }

            for _, exe in ipairs(runtime_executables) do
                local real_exe = file.join_path(real_bin_dir, exe)
                local wrapper_exe = file.join_path(wrapper_bin_dir, exe)
                local write_wrapper_cmd = string.format([[
if [ -f '%s' ]; then
    cat > '%s' << 'WRAPEOF'
#!/bin/bash
# Wrapper that sets LD_LIBRARY_PATH for Nix Ruby runtime
export LD_LIBRARY_PATH='%s'
exec '%s' "$@"
WRAPEOF
    chmod +x '%s'
fi
]], real_exe, wrapper_exe, ld_library_path, real_exe, wrapper_exe)
                cmd.exec(write_wrapper_cmd)
            end

            -- Compilation wrappers - no LD_LIBRARY_PATH to avoid breaking system tools
            for _, exe in ipairs(compile_executables) do
                local real_exe = file.join_path(real_bin_dir, exe)
                local wrapper_exe = file.join_path(wrapper_bin_dir, exe)
                local write_wrapper_cmd = string.format([[
if [ -f '%s' ]; then
    cat > '%s' << 'WRAPEOF'
#!/bin/bash
# Wrapper for Nix Ruby (no LD_LIBRARY_PATH to avoid breaking system tools during compilation)
exec '%s' "$@"
WRAPEOF
    chmod +x '%s'
fi
]], real_exe, wrapper_exe, real_exe, wrapper_exe)
                cmd.exec(write_wrapper_cmd)
            end
        end
    end

    return {}
end
