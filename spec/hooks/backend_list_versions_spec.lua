describe("PLUGIN:BackendListVersions", function()
	local mock_runtime = require("spec.helpers.mock_runtime")
	local mock_modules = require("spec.helpers.mock_modules")
	local fixtures = require("spec.helpers.fixtures")

	before_each(function()
		mock_modules.clear_modules()
		mock_runtime.restore_runtime()
		_G.PLUGIN = {}
		package.loaded["hooks.backend_list_versions"] = nil
	end)

	local function load_hook()
		dofile("hooks/backend_list_versions.lua")
		return _G.PLUGIN
	end

	it("lists versions for ruby on x86_64-linux", function()
		mock_runtime.inject_runtime(mock_runtime.create_runtime({
			osType = "linux",
			archType = "amd64",
		}))

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

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
		})

		local plugin = load_hook()
		local result = plugin:BackendListVersions({ tool = "ruby" })

		assert.is_not_nil(result.versions)
		assert.is_true(#result.versions >= 1)
		assert.is_true(result.versions[1] == "3.3.9" or result.versions[1] == "3.3.8")
	end)

	it("filters versions by platform", function()
		mock_runtime.inject_runtime(mock_runtime.create_runtime({
			osType = "darwin",
			archType = "arm64",
		}))

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

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
		})

		local plugin = load_hook()
		local result = plugin:BackendListVersions({ tool = "ruby" })

		assert.equals(1, #result.versions)
		assert.equals("3.3.9", result.versions[1])
	end)

	it("errors when tool name is empty", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendListVersions({ tool = "" })
		end, "Tool name cannot be empty")
	end)

	it("errors when tool is nil", function()
		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendListVersions({ tool = nil })
		end, "Tool name cannot be empty")
	end)

	it("errors when tool not found in mapping", function()
		mock_runtime.inject_runtime(mock_runtime.create_runtime())

		local nix_mock = {
			current_system = function()
				return "x86_64-linux"
			end,
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return { pkgs = {} }
			end,
		}

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
		})

		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendListVersions({ tool = "nonexistent" })
		end, "Tool nonexistent not found in mapping")
	end)

	it("errors when no versions available for platform", function()
		mock_runtime.inject_runtime(mock_runtime.create_runtime())

		local nix_mock = {
			current_system = function()
				return "x86_64-linux"
			end,
		}

		local mapping_with_no_versions = {
			pkgs = {
				ruby = {
					["3.3.9"] = {
						store_paths = {
							["aarch64-darwin"] = "/nix/store/hash-ruby",
						},
					},
				},
			},
		}

		local nixpkgs_mapping_mock = {
			parse_mapping_file = function()
				return mapping_with_no_versions
			end,
		}

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
		})

		local plugin = load_hook()

		assert.has_error(function()
			plugin:BackendListVersions({ tool = "ruby" })
		end, "No versions found for ruby")
	end)

	it("sorts versions semantically not lexicographically", function()
		mock_runtime.inject_runtime(mock_runtime.create_runtime({
			osType = "linux",
			archType = "amd64",
		}))

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

		mock_modules.inject_modules({
			["lib.nix"] = nix_mock,
			["lib.nixpkgs_mapping"] = nixpkgs_mapping_mock,
		})

		local plugin = load_hook()
		local result = plugin:BackendListVersions({ tool = "go" })

		assert.equals(9, #result.versions)
		assert.equals("1.0.2", result.versions[1])
		assert.equals("1.0.10", result.versions[2])
		assert.equals("1.9.0", result.versions[3])
		assert.equals("1.10.0", result.versions[4])
		assert.equals("2.0.0", result.versions[5])
		-- According to semver, pre-release versions come before the release version
		assert.equals("3.14.0-rc1", result.versions[6])
		assert.equals("3.14.0-rc2", result.versions[7])
		assert.equals("3.14.0", result.versions[8])
		-- 3.14.0rc99 is not a valid semver (missing hyphen), so it's treated as
		-- a version with extra text and sorts after 3.14.0
		assert.equals("3.14.0rc99", result.versions[9])
	end)
end)
