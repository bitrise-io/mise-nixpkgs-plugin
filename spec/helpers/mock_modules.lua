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

function M.mock_cmd_module()
    return {
        exec = function(cmd)
            return "success"
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
