local M = {}

-- Parse a version string into core version and prerelease parts
-- Returns: parts (numeric array), prerelease (string or nil), suffix (non-semver text or nil)
local function parse_version(version)
    -- Try to match semver format: X.Y.Z-prerelease
    local core, prerelease = version:match("^([%d%.]+)%-(.+)$")
    if core then
        local parts = {}
        for part in string.gmatch(core, "%d+") do
            table.insert(parts, tonumber(part))
        end
        return parts, prerelease, nil
    end

    -- Try to match just numeric version with optional suffix (non-semver)
    core = version:match("^([%d%.]+)")
    if not core then
        return {}, nil, version
    end

    local parts = {}
    for part in string.gmatch(core, "%d+") do
        table.insert(parts, tonumber(part))
    end

    -- Check if there's anything after the numeric part (non-semver suffix)
    local suffix = version:sub(#core + 1)
    if suffix and suffix ~= "" then
        return parts, nil, suffix
    end

    return parts, nil, nil
end

-- Compare two prerelease strings according to semver rules
-- Returns: -1 if pr1 < pr2, 0 if equal, 1 if pr1 > pr2
local function compare_prerelease(pr1, pr2)
    if not pr1 and not pr2 then
        return 0
    end
    if not pr1 then
        return 1
    end
    if not pr2 then
        return -1
    end

    local pr1_parts = {}
    for part in string.gmatch(pr1, "[^%.]+") do
        table.insert(pr1_parts, part)
    end

    local pr2_parts = {}
    for part in string.gmatch(pr2, "[^%.]+") do
        table.insert(pr2_parts, part)
    end

    for i = 1, math.max(#pr1_parts, #pr2_parts) do
        local p1 = pr1_parts[i]
        local p2 = pr2_parts[i]

        if not p1 then
            return -1
        end
        if not p2 then
            return 1
        end

        local p1_num = tonumber(p1)
        local p2_num = tonumber(p2)

        if p1_num and p2_num then
            if p1_num > p2_num then
                return 1
            elseif p1_num < p2_num then
                return -1
            end
        elseif p1_num then
            return -1
        elseif p2_num then
            return 1
        else
            if p1 > p2 then
                return 1
            elseif p1 < p2 then
                return -1
            end
        end
    end

    return 0
end

-- Compare two version strings according to semver rules
-- Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
function M.compare_versions(v1, v2)
    local v1_parts, v1_prerelease, v1_suffix = parse_version(v1)
    local v2_parts, v2_prerelease, v2_suffix = parse_version(v2)

    -- Compare numeric version parts
    for i = 1, math.max(#v1_parts, #v2_parts) do
        local v1_part = v1_parts[i] or 0
        local v2_part = v2_parts[i] or 0
        if v1_part > v2_part then
            return 1
        elseif v1_part < v2_part then
            return -1
        end
    end

    -- If numeric parts are equal, compare prereleases
    local prerelease_cmp = compare_prerelease(v1_prerelease, v2_prerelease)
    if prerelease_cmp ~= 0 then
        return prerelease_cmp
    end

    -- If both are equal so far, handle non-semver suffixes
    -- Versions with suffixes sort after versions without suffixes
    if not v1_suffix and not v2_suffix then
        return 0
    end
    if not v1_suffix then
        return -1
    end
    if not v2_suffix then
        return 1
    end
    
    -- Both have suffixes, compare lexically
    if v1_suffix < v2_suffix then
        return -1
    elseif v1_suffix > v2_suffix then
        return 1
    end
    
    return 0
end

return M
