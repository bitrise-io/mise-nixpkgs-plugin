describe("PLUGIN:BackendExecEnv", function()
    local mock_modules = require("spec.helpers.mock_modules")

    before_each(function()
        mock_modules.clear_modules()
        _G.PLUGIN = {}
        package.loaded["hooks.backend_exec_env"] = nil
    end)

    local function load_hook()
        dofile("hooks/backend_exec_env.lua")
        return _G.PLUGIN
    end

    it("sets PATH for generic tool", function()
        local file_mock = mock_modules.mock_file_module()
        mock_modules.inject_modules({ file = file_mock })

        local plugin = load_hook()
        local result = plugin:BackendExecEnv({
            install_path = "/home/user/.local/share/mise/installs/nixpkgs-node/20.1.0",
            tool = "node",
            version = "20.1.0",
        })

        assert.is_not_nil(result.env_vars)
        assert.is_true(#result.env_vars >= 1)

        local found_path = false
        for _, env_var in ipairs(result.env_vars) do
            if env_var.key == "PATH" and env_var.value:match("/result/bin$") then
                found_path = true
                break
            end
        end
        assert.is_true(found_path)
    end)

    it("sets MANPATH for all tools", function()
        local file_mock = mock_modules.mock_file_module()
        mock_modules.inject_modules({ file = file_mock })

        local plugin = load_hook()
        local result = plugin:BackendExecEnv({
            install_path = "/home/user/.local/share/mise/installs/nixpkgs-node/20.1.0",
            tool = "node",
            version = "20.1.0",
        })

        local found_manpath = false
        for _, env_var in ipairs(result.env_vars) do
            if env_var.key == "MANPATH" and env_var.value:match("/share/man$") then
                found_manpath = true
                break
            end
        end
        assert.is_true(found_manpath)
    end)

    it("sets ruby-specific environment variables", function()
        local file_mock = mock_modules.mock_file_module()
        mock_modules.inject_modules({ file = file_mock })

        local plugin = load_hook()
        local result = plugin:BackendExecEnv({
            install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
            tool = "ruby",
            version = "3.3.9",
        })

        assert.is_not_nil(result.env_vars)

        local found_gem_home = false
        local found_gem_path = false
        local found_gems_bin_path = false

        for _, env_var in ipairs(result.env_vars) do
            if env_var.key == "GEM_HOME" and env_var.value:match("/state/gems$") then
                found_gem_home = true
            end
            if env_var.key == "GEM_PATH" and env_var.value:match("/state/gems/gems$") then
                found_gem_path = true
            end
            if env_var.key == "PATH" and env_var.value:match("/state/gems/bin$") then
                found_gems_bin_path = true
            end
        end

        assert.is_true(found_gem_home, "GEM_HOME not found")
        assert.is_true(found_gem_path, "GEM_PATH not found")
        assert.is_true(found_gems_bin_path, "gems/bin PATH not found")
    end)

    it("returns correct PATH structure for ruby", function()
        local file_mock = mock_modules.mock_file_module()
        mock_modules.inject_modules({ file = file_mock })

        local plugin = load_hook()
        local result = plugin:BackendExecEnv({
            install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
            tool = "ruby",
            version = "3.3.9",
        })

        -- Note: our Lua hook simply add two PATH entries for ruby, Mise handles deduplication and merging.
        local path_count = 0
        for _, env_var in ipairs(result.env_vars) do
            if env_var.key == "PATH" then
                path_count = path_count + 1
            end
        end

        assert.equals(2, path_count)
    end)
end)
