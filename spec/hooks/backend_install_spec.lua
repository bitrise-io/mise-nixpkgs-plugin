describe("PLUGIN:BackendInstall validation", function()
	local mock_modules = require("spec.helpers.mock_modules")
	local fixtures = require("spec.helpers.fixtures")

	before_each(function()
		mock_modules.clear_modules()
		_G.PLUGIN = {}
		package.loaded["hooks.backend_install"] = nil
	end)

	local function load_hook()
		dofile("hooks/backend_install.lua")
		return _G.PLUGIN
	end

	it("errors when tool name is empty", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = "",
				version = "3.3.9",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			})
		end, "Tool name cannot be empty")
	end)

	it("errors when tool name is nil", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = nil,
				version = "3.3.9",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			})
		end, "Tool name cannot be empty")
	end)

	it("errors when version is empty", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			})
		end, "Version cannot be empty")
	end)

	it("errors when version is nil", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = nil,
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			})
		end, "Version cannot be empty")
	end)

	it("errors when install_path is empty", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "3.3.9",
				install_path = "",
			})
		end, "Install path cannot be empty")
	end)

	it("errors when install_path is nil", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "3.3.9",
				install_path = nil,
			})
		end, "Install path cannot be empty")
	end)

	it("errors when mapping has no pkgs", function()
		local nix_mock = {
			current_system = function()
				return "x86_64-linux"
			end,
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return {}
			end,
		}

		local cmd_mock = mock_modules.mock_cmd_module()

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
			cmd = cmd_mock,
		})

		local plugin = load_hook()

		local success, err = pcall(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "3.3.9",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.9",
			})
		end)

		assert.is_false(success)
		assert.is_not_nil(err:match("No nixpkgs mapping found for ruby@3.3.9 on x86_64%-linux"))
	end)

	it("errors when tool not in mapping", function()
		local nix_mock = {
			current_system = function()
				return "x86_64-linux"
			end,
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return fixtures.sample_index
			end,
		}

		local cmd_mock = mock_modules.mock_cmd_module()

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
			cmd = cmd_mock,
		})

		local plugin = load_hook()

		local success, err = pcall(function()
			plugin:BackendInstall({
				tool = "nonexistent",
				version = "1.0.0",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-nonexistent/1.0.0",
			})
		end)

		assert.is_false(success)
		assert.is_not_nil(err:match("No nixpkgs mapping found for nonexistent@1.0.0 on x86_64%-linux"))
	end)

	it("errors when version not in mapping", function()
		local nix_mock = {
			current_system = function()
				return "x86_64-linux"
			end,
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return fixtures.sample_index
			end,
		}

		local cmd_mock = mock_modules.mock_cmd_module()

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
			cmd = cmd_mock,
		})

		local plugin = load_hook()

		local success, err = pcall(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "999.999.999",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/999.999.999",
			})
		end)

		assert.is_false(success)
		assert.is_not_nil(err:match("No nixpkgs mapping found for ruby@999.999.999 on x86_64%-linux"))
	end)

	it("errors when platform not in store_paths", function()
		local nix_mock = {
			current_system = function()
				return "aarch64-darwin"
			end,
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return fixtures.sample_index
			end,
		}

		local cmd_mock = mock_modules.mock_cmd_module()

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
			cmd = cmd_mock,
		})

		local plugin = load_hook()

		local success, err = pcall(function()
			plugin:BackendInstall({
				tool = "ruby",
				version = "3.3.8",
				install_path = "/home/user/.local/share/mise/installs/nixpkgs-ruby/3.3.8",
			})
		end)

		assert.is_false(success)
		assert.is_not_nil(err:match("No nixpkgs mapping found for ruby@3.3.8 on aarch64%-darwin"))
	end)
end)
