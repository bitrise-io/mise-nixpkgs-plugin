local M = {}

function M.create_runtime(opts)
	opts = opts or {}
	return {
		osType = opts.osType or "linux",
		archType = opts.archType or "amd64",
		pluginDirPath = opts.pluginDirPath or "/tmp/test-plugin",
	}
end

function M.inject_runtime(runtime)
	_G.RUNTIME = runtime
end

function M.restore_runtime()
	_G.RUNTIME = nil
end

return M
