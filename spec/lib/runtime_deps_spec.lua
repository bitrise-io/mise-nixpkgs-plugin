describe("runtime_deps", function()
    local runtime_deps
    local mock_modules = require("spec.helpers.mock_modules")

    before_each(function()
        package.loaded["lib.runtime_deps"] = nil
        mock_modules.clear_modules()
    end)

    describe("find_lib_paths", function()
        before_each(function()
            runtime_deps = require("lib.runtime_deps")
        end)

        it("finds lib directories in store paths", function()
            local store_paths = {
                "/nix/store/abc123-package-1.0",
                "/nix/store/def456-dep-2.0",
                "/nix/store/ghi789-other-3.0",
            }

            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    if cmd:match("abc123") or cmd:match("def456") then
                        return "exists"
                    end
                    return ""
                end,
            }

            local result = runtime_deps.find_lib_paths(store_paths, file_mock, cmd_mock)
            assert.equals(2, #result)
            assert.equals("/nix/store/abc123-package-1.0/lib", result[1])
            assert.equals("/nix/store/def456-dep-2.0/lib", result[2])
        end)

        it("returns empty list when no lib directories exist", function()
            local store_paths = {
                "/nix/store/abc123-package-1.0",
                "/nix/store/def456-dep-2.0",
            }

            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    return ""
                end,
            }

            local result = runtime_deps.find_lib_paths(store_paths, file_mock, cmd_mock)
            assert.equals(0, #result)
        end)

        it("handles empty store paths list", function()
            local store_paths = {}
            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = mock_modules.mock_cmd_module()

            local result = runtime_deps.find_lib_paths(store_paths, file_mock, cmd_mock)
            assert.equals(0, #result)
        end)
    end)

    describe("find_pkgconfig_paths", function()
        before_each(function()
            runtime_deps = require("lib.runtime_deps")
        end)

        it("finds lib/pkgconfig directories in store paths", function()
            local store_paths = {
                "/nix/store/abc123-package-1.0",
                "/nix/store/def456-dep-2.0",
                "/nix/store/ghi789-other-3.0",
            }

            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    if
                        cmd:match("/nix/store/abc123%-package%-1%.0/lib/pkgconfig")
                        or cmd:match("/nix/store/ghi789%-other%-3%.0/lib/pkgconfig")
                    then
                        return "exists"
                    end
                    return ""
                end,
            }

            local result = runtime_deps.find_pkgconfig_paths(store_paths, file_mock, cmd_mock)
            assert.equals(2, #result)
            assert.equals("/nix/store/abc123-package-1.0/lib/pkgconfig", result[1])
            assert.equals("/nix/store/ghi789-other-3.0/lib/pkgconfig", result[2])
        end)

        it("returns empty list when no pkgconfig directories exist", function()
            local store_paths = {
                "/nix/store/abc123-package-1.0",
                "/nix/store/def456-dep-2.0",
            }

            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    return ""
                end,
            }

            local result = runtime_deps.find_pkgconfig_paths(store_paths, file_mock, cmd_mock)
            assert.equals(0, #result)
        end)

        it("handles empty store paths list", function()
            local store_paths = {}
            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = mock_modules.mock_cmd_module()

            local result = runtime_deps.find_pkgconfig_paths(store_paths, file_mock, cmd_mock)
            assert.equals(0, #result)
        end)
    end)

    describe("create_library_env_vars", function()
        before_each(function()
            runtime_deps = require("lib.runtime_deps")
        end)

        it("creates LD_LIBRARY_PATH env vars for linux", function()
            local lib_paths = {
                "/nix/store/abc123-package-1.0/lib",
                "/nix/store/def456-dep-2.0/lib",
            }

            local result = runtime_deps.create_library_env_vars(lib_paths, "linux")
            assert.equals(2, #result)
            assert.equals("LD_LIBRARY_PATH", result[1].key)
            assert.equals("/nix/store/abc123-package-1.0/lib", result[1].value)
            assert.equals("LD_LIBRARY_PATH", result[2].key)
            assert.equals("/nix/store/def456-dep-2.0/lib", result[2].value)
        end)

        it("creates DYLD_LIBRARY_PATH env vars for darwin", function()
            local lib_paths = {
                "/nix/store/abc123-package-1.0/lib",
                "/nix/store/def456-dep-2.0/lib",
            }

            local result = runtime_deps.create_library_env_vars(lib_paths, "darwin")
            assert.equals(2, #result)
            assert.equals("DYLD_LIBRARY_PATH", result[1].key)
            assert.equals("/nix/store/abc123-package-1.0/lib", result[1].value)
            assert.equals("DYLD_LIBRARY_PATH", result[2].key)
            assert.equals("/nix/store/def456-dep-2.0/lib", result[2].value)
        end)

        it("returns error for unsupported os_type", function()
            local lib_paths = {
                "/nix/store/abc123-package-1.0/lib",
            }

            local success, result = pcall(function()
                runtime_deps.create_library_env_vars(lib_paths, "windows")
            end)

            assert.is_false(success)
            assert.is_not_nil(result:match("Unsupported architecture: windows"))
        end)

        it("handles empty lib_paths list", function()
            local lib_paths = {}

            local result = runtime_deps.create_library_env_vars(lib_paths, "linux")
            assert.equals(0, #result)
        end)
    end)

    describe("create_pkgconfig_env_vars", function()
        before_each(function()
            runtime_deps = require("lib.runtime_deps")
        end)

        it("creates PKG_CONFIG_PATH env vars", function()
            local pkgconfig_paths = {
                "/nix/store/abc123-package-1.0/lib/pkgconfig",
                "/nix/store/def456-dep-2.0/lib/pkgconfig",
            }

            local result = runtime_deps.create_pkgconfig_env_vars(pkgconfig_paths)
            assert.equals(2, #result)
            assert.equals("PKG_CONFIG_PATH", result[1].key)
            assert.equals("/nix/store/abc123-package-1.0/lib/pkgconfig", result[1].value)
            assert.equals("PKG_CONFIG_PATH", result[2].key)
            assert.equals("/nix/store/def456-dep-2.0/lib/pkgconfig", result[2].value)
        end)

        it("handles empty pkgconfig_paths list", function()
            local pkgconfig_paths = {}

            local result = runtime_deps.create_pkgconfig_env_vars(pkgconfig_paths)
            assert.equals(0, #result)
        end)
    end)

    describe("get_runtime_dep_env_vars", function()
        it("returns combined env vars for successful query on linux", function()
            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    if cmd:match("nix%-store %-%-query %-%-requisites") then
                        return "/nix/store/1254dv820b6xp5gw9fjz9i0rjxxx3fkh-libffi-39\n"
                            .. "/nix/store/l619460n5l5jgg2y3b3y6k11q4l462d5-libcxx-19.1.7\n"
                            .. "/nix/store/p1llvdzvsgy9bgjcxiadhzrp2kv2dd3a-zlib-1.3.1\n"
                            .. "/nix/store/pff8c9a4l487r0jaipibq21mkww5f1yw-libiconv-109\n"
                            .. "/nix/store/qz8sy946bfh14jb90wagc43q5clnzxp4-libxml2-2.14.5\n"
                            .. "/nix/store/6wb8wlgfpqw1n2f0r0x4qqxkp2g67q53-llvm-19.1.7-lib\n"
                            .. "/nix/store/vhpaiaa94mqzivqkzjrad6af72irp89j-openssl-3.5.1\n"
                            .. "/nix/store/z5dn71p2v8zs4ivli9ki35m6bm50fli4-ruby-3.3.8"
                    elseif
                        -- dir existence check
                        cmd:match("1254dv820b6xp5gw9fjz9i0rjxxx3fkh")
                        or cmd:match("p1llvdzvsgy9bgjcxiadhzrp2kv2dd3a")
                        or cmd:match("vhpaiaa94mqzivqkzjrad6af72irp89j")
                    then
                        return "exists"
                    end
                    return ""
                end,
            }

            mock_modules.inject_modules({ file = file_mock, cmd = cmd_mock })
            runtime_deps = require("lib.runtime_deps")

            local result = runtime_deps.get_env_vars(
                "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.8",
                "ruby",
                "3.3.8",
                "linux"
            )

            assert.is_not_nil(result)
            assert.is_true(#result > 0)

            local found_ld_library_path = false
            local found_pkg_config_path = false
            for _, env_var in ipairs(result) do
                if env_var.key == "LD_LIBRARY_PATH" then
                    found_ld_library_path = true
                end
                if env_var.key == "PKG_CONFIG_PATH" then
                    found_pkg_config_path = true
                end
            end

            assert.is_true(found_ld_library_path)
            assert.is_true(found_pkg_config_path)
        end)

        it("returns combined env vars for successful query on darwin", function()
            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    if cmd:match("nix%-store %-%-query %-%-requisites") then
                        return "/nix/store/1254dv820b6xp5gw9fjz9i0rjxxx3fkh-libffi-39\n"
                            .. "/nix/store/p1llvdzvsgy9bgjcxiadhzrp2kv2dd3a-zlib-1.3.1\n"
                            .. "/nix/store/qz8sy946bfh14jb90wagc43q5clnzxp4-libxml2-2.14.5\n"
                            .. "/nix/store/vhpaiaa94mqzivqkzjrad6af72irp89j-openssl-3.5.1"
                    elseif
                        -- dir existence check
                        cmd:match("1254dv820b6xp5gw9fjz9i0rjxxx3fkh") or cmd:match("vhpaiaa94mqzivqkzjrad6af72irp89j")
                    then
                        return "exists"
                    end
                    return ""
                end,
            }

            mock_modules.inject_modules({ file = file_mock, cmd = cmd_mock })
            runtime_deps = require("lib.runtime_deps")

            local result = runtime_deps.get_env_vars(
                "/Users/user/.local/share/mise/installs/nixpkgs-ruby/3.3.8",
                "ruby",
                "3.3.8",
                "darwin"
            )

            assert.is_not_nil(result)
            assert.is_true(#result > 0)

            local found_dyld_library_path = false
            local found_pkg_config_path = false
            for _, env_var in ipairs(result) do
                if env_var.key == "DYLD_LIBRARY_PATH" then
                    found_dyld_library_path = true
                end
                if env_var.key == "PKG_CONFIG_PATH" then
                    found_pkg_config_path = true
                end
            end

            assert.is_true(found_dyld_library_path)
            assert.is_true(found_pkg_config_path)
        end)

        it("returns empty env vars when no lib or pkgconfig directories found", function()
            local file_mock = mock_modules.mock_file_module()
            local cmd_mock = {
                exec = function(cmd)
                    if cmd:match("nix%-store") then
                        return "/nix/store/abc123-package-1.0"
                    end
                    return ""
                end,
            }

            mock_modules.inject_modules({ file = file_mock, cmd = cmd_mock })
            runtime_deps = require("lib.runtime_deps")

            local result = runtime_deps.get_env_vars(
                "/home/user/.local/share/mise/installs/nixpkgs-node/20.1.0",
                "node",
                "20.1.0",
                "linux"
            )

            assert.equals(0, #result)
        end)
    end)
end)
