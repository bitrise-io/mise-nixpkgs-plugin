local M = {}

function M.mock_file_module()
	return {
		read = function(path)
			return '{"pkgs":{}}'
		end,
		join_path = function(...)
			return table.concat({ ... }, "/")
		end,
	}
end

function M.mock_cmd_module(exec_results)
	exec_results = exec_results or {}
	return {
		exec = function(cmd)
			-- Check if we have a specific result for this command pattern
			for pattern, result in pairs(exec_results) do
				if cmd:match(pattern) then
					return result
				end
			end
			return "success"
		end,
	}
end

function M.mock_nix_module(opts)
	opts = opts or {}
	return {
		is_linux = function()
			return opts.is_linux or false
		end,
		is_darwin = function()
			return opts.is_darwin or false
		end,
		get_store_dependency = function(store_path, pattern)
			if opts.store_dependencies and opts.store_dependencies[pattern] then
				return opts.store_dependencies[pattern]
			end
			return nil
		end,
		current_system = function()
			return opts.current_system or "x86_64-linux"
		end,
	}
end

function M.inject_modules(mocks)
	for name, mock in pairs(mocks) do
		package.loaded[name] = mock
	end
end

function M.clear_modules()
	package.loaded["file"] = nil
	package.loaded["json"] = nil
	package.loaded["cmd"] = nil
	package.loaded["lib.nix"] = nil
	package.loaded["lib.nixpkgs_mapping"] = nil
end

return M
