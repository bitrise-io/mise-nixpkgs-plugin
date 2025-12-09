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
	},
}

M.sample_json = function()
	local json = require("json")
	return json.encode(M.sample_index)
end

return M
