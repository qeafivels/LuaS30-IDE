local E = engine

local M = {}

function M.screen()
    return E.W or 240, E.H or 320
end

function M.rgb(r, g, b)
    return E.color(r, g, b)
end

function M.save(name, data)
    return E.file_write(name, data)
end

function M.load(name)
    return E.file_read(name)
end

return M
