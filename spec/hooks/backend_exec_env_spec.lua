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

	it("sets ruby-specific environment variables on darwin (no Linux glibc workaround)", function()
		local file_mock = mock_modules.mock_file_module()
		local nix_mock = mock_modules.mock_nix_module({ is_linux = false, is_darwin = true })
		mock_modules.inject_modules({ file = file_mock, ["lib.nix"] = nix_mock })

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
		local found_rubyopt = false
		local found_cc = false
		local found_ld_library_path = false

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
			if env_var.key == "RUBYOPT" then
				found_rubyopt = true
			end
			if env_var.key == "CC" then
				found_cc = true
			end
			if env_var.key == "LD_LIBRARY_PATH" then
				found_ld_library_path = true
			end
		end

		assert.is_true(found_gem_home, "GEM_HOME not found")
		assert.is_true(found_gem_path, "GEM_PATH not found")
		assert.is_true(found_gems_bin_path, "gems/bin PATH not found")
		-- Linux-specific env vars should NOT be set on darwin
		assert.is_false(found_rubyopt, "RUBYOPT should not be set on darwin")
		assert.is_false(found_cc, "CC should not be set on darwin")
		assert.is_false(found_ld_library_path, "LD_LIBRARY_PATH should not be set on darwin")
	end)

	it("sets RUBYOPT, CC, and LD_LIBRARY_PATH for ruby on linux", function()
		local file_mock = mock_modules.mock_file_module()
		local nix_mock = mock_modules.mock_nix_module({
			is_linux = true,
			is_darwin = false,
			current_system = "x86_64-linux",
			store_dependencies = {
				["glibc"] = "/nix/store/abc123-glibc-2.40",
				["gcc.*lib"] = "/nix/store/def456-gcc-lib",
			},
		})
		mock_modules.inject_modules({ file = file_mock, ["lib.nix"] = nix_mock })

		local plugin = load_hook()
		local result = plugin:BackendExecEnv({
			install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			tool = "ruby",
			version = "3.3.9",
		})

		assert.is_not_nil(result.env_vars)

		local rubyopt_value = nil
		local cc_value = nil
		local ld_library_path_value = nil

		for _, env_var in ipairs(result.env_vars) do
			if env_var.key == "RUBYOPT" then
				rubyopt_value = env_var.value
			end
			if env_var.key == "CC" then
				cc_value = env_var.value
			end
			if env_var.key == "LD_LIBRARY_PATH" then
				ld_library_path_value = env_var.value
			end
		end

		-- Check RUBYOPT points to the ldflags injection script
		assert.is_not_nil(rubyopt_value, "RUBYOPT not found")
		assert.is_truthy(rubyopt_value:match("ldflags_inject%.rb"))

		-- Check CC points to the gcc wrapper
		assert.is_not_nil(cc_value, "CC not found")
		assert.is_truthy(cc_value:match("gcc%-wrapper"))

		-- Check LD_LIBRARY_PATH contains Nix paths first, then system paths
		assert.is_not_nil(ld_library_path_value, "LD_LIBRARY_PATH not found")
		assert.is_truthy(ld_library_path_value:match("/nix/store/abc123%-glibc%-2%.40/lib"))
		assert.is_truthy(ld_library_path_value:match("/nix/store/def456%-gcc%-lib/lib"))
	end)

	it("does not set Linux glibc workaround vars if glibc dependency not found", function()
		local file_mock = mock_modules.mock_file_module()
		local nix_mock = mock_modules.mock_nix_module({
			is_linux = true,
			is_darwin = false,
			store_dependencies = {
				-- glibc not found, only gcc-lib
				["gcc.*lib"] = "/nix/store/def456-gcc-lib",
			},
		})
		mock_modules.inject_modules({ file = file_mock, ["lib.nix"] = nix_mock })

		local plugin = load_hook()
		local result = plugin:BackendExecEnv({
			install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			tool = "ruby",
			version = "3.3.9",
		})

		local found_rubyopt = false
		local found_cc = false
		for _, env_var in ipairs(result.env_vars) do
			if env_var.key == "RUBYOPT" then
				found_rubyopt = true
			end
			if env_var.key == "CC" then
				found_cc = true
			end
		end

		assert.is_false(found_rubyopt, "RUBYOPT should not be set when glibc is not found")
		assert.is_false(found_cc, "CC should not be set when glibc is not found")
	end)

	it("returns correct PATH structure for ruby", function()
		local file_mock = mock_modules.mock_file_module()
		local nix_mock = mock_modules.mock_nix_module({ is_linux = false, is_darwin = true })
		mock_modules.inject_modules({ file = file_mock, ["lib.nix"] = nix_mock })

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
