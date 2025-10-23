local file = require("file")
local json = require("json")

local M = {}

function M.parse_mapping_file()
    local file_path = RUNTIME.pluginDirPath .. "/nixpkgs-mapping.json"

    -- TODO: file.exists() doesn't exist 🤷
    -- if not file.exists(config_path) then
    --     return {}  -- Return empty config
    -- end

    local content = file.read(file_path)
    if not content then
        error("Failed to read mapping file: " .. file_path)
    end

    -- Parse JSON
    local success, mapping = pcall(json.decode, content)
    if not success then
        error("Invalid JSON in mapping file: " .. file_path)
    end

    return mapping
end

return M
