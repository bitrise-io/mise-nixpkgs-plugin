local M = {}

M.sample_index = {
	pkgs = {
		ruby = {
			["3.3.9"] = {
				nixpkgs_commit = "abc123def456",
				commit_timestamp = "2025-01-15T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash1-ruby-3.3.9",
					["aarch64-darwin"] = "/nix/store/hash2-ruby-3.3.9",
				},
			},
			["3.3.8"] = {
				nixpkgs_commit = "def456abc789",
				commit_timestamp = "2025-01-14T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash3-ruby-3.3.8",
					-- Note: aarch64-darwin entry is intentionally missing for testing
				},
			},
		},
		python = {
			["3.12.1"] = {
				nixpkgs_commit = "ghi789jkl012",
				commit_timestamp = "2025-01-16T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash4-python-3.12.1",
					["aarch64-darwin"] = "/nix/store/hash5-python-3.12.1",
				},
			},
		},
		go = {
			["1.9.0"] = {
				nixpkgs_commit = "commit1",
				commit_timestamp = "2025-01-01T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-1.9.0",
				},
			},
			["1.0.2"] = {
				nixpkgs_commit = "commit2",
				commit_timestamp = "2025-01-02T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-1.0.2",
				},
			},
			["1.10.0"] = {
				nixpkgs_commit = "commit3",
				commit_timestamp = "2025-01-03T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-1.10.0",
				},
			},
			["1.0.10"] = {
				nixpkgs_commit = "commit4",
				commit_timestamp = "2025-01-04T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-1.0.10",
				},
			},
			["2.0.0"] = {
				nixpkgs_commit = "commit5",
				commit_timestamp = "2025-01-05T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-2.0.0",
				},
			},
			["3.14.0-rc1"] = {
				nixpkgs_commit = "commit6",
				commit_timestamp = "2025-01-06T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-3.14.0-rc1",
				},
			},
			["3.14.0-rc2"] = {
				nixpkgs_commit = "commit7",
				commit_timestamp = "2025-01-07T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-3.14.0-rc2",
				},
			},
			["3.14.0"] = {
				nixpkgs_commit = "commit8",
				commit_timestamp = "2025-01-08T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-3.14.0",
				},
			},
			["3.14.0rc99"] = {
				nixpkgs_commit = "commit9",
				commit_timestamp = "2025-01-09T12:00:00+00:00",
				store_paths = {
					["x86_64-linux"] = "/nix/store/hash-go-3.14.0rc99",
				},
			},
		},
	},
}

M.sample_json = function()
	local json = require("json")
	return json.encode(M.sample_index)
end

return M
