-- Procedural notebook/doodle renderer. No external bitmap assets required.
local E = engine
local M = {}

local cache = {}
function M.col(r, g, b)
    local key = r * 65536 + g * 256 + b
    local c = cache[key]
    if not c then
        c = E.color(r, g, b)
        cache[key] = c
    end
    return c
end

local C = {
    paper = M.col(246, 242, 220),
    paper2 = M.col(238, 233, 205),
    line = M.col(173, 198, 212),
    margin = M.col(218, 92, 92),
    ink = M.col(25, 44, 78),
    ink2 = M.col(52, 73, 112),
    pencil = M.col(96, 91, 82),
    white = M.col(255, 255, 247),
    accent = M.col(244, 142, 54),
    accent2 = M.col(233, 96, 68),
    green = M.col(76, 145, 86),
    shadow = M.col(206, 199, 174),
    dark = M.col(37, 38, 43),
}
M.C = C

function M.rect(x, y, w, h, color)
    if w <= 0 or h <= 0 then return end
    local x2, y2 = x + w, y + h
    if x < 0 then x = 0 end
    if y < 0 then y = 0 end
    if x2 > 240 then x2 = 240 end
    if y2 > 320 then y2 = 320 end
    if x2 > x and y2 > y then
        E.rect(math.floor(x), math.floor(y), math.floor(x2 - x), math.floor(y2 - y), color)
    end
end

function M.paper()
    E.clear(C.paper)
    for y = 24, 319, 16 do
        M.rect(0, y, 240, 1, C.line)
    end
    M.rect(20, 0, 1, 320, C.margin)
    M.rect(22, 0, 1, 320, C.margin)
    -- notebook holes
    for y = 20, 300, 36 do
        M.rect(6, y, 6, 6, C.shadow)
        M.rect(7, y + 1, 4, 4, C.paper2)
    end
end

function M.text_center(y, text, color)
    local w = E.text_width(text)
    E.text(math.floor((240 - w) / 2), y, text, color)
end

function M.title(text)
    M.rect(28, 10, 184, 28, C.white)
    E.frame(28, 10, 184, 28, C.ink)
    M.text_center(18, text, C.ink)
    M.rect(34, 37, 172, 2, C.accent)
end

function M.button(y, label, selected)
    local x, w, h = 38, 164, 28
    M.rect(x + 2, y + 2, w, h, C.shadow)
    M.rect(x, y, w, h, selected and C.white or C.paper2)
    E.frame(x, y, w, h, selected and C.accent2 or C.ink2)
    if selected then
        M.rect(x + 4, y + 4, 4, h - 8, C.accent)
        E.text(x + 13, y + 9, ">", C.accent2)
    end
    local tx = x + math.floor((w - E.text_width(label)) / 2)
    E.text(tx, y + 9, label, selected and C.ink or C.ink2)
end

function M.panel(x, y, w, h)
    M.rect(x + 3, y + 3, w, h, C.shadow)
    M.rect(x, y, w, h, C.white)
    E.frame(x, y, w, h, C.ink2)
end

function M.star(x, y, color)
    color = color or C.accent
    M.rect(x + 3, y, 3, 9, color)
    M.rect(x, y + 3, 9, 3, color)
    M.rect(x + 1, y + 1, 7, 7, color)
    M.rect(x + 3, y + 3, 3, 3, C.white)
end

function M.player(x, y, frame)
    -- simple doodle character, 14x18
    local bob = frame % 2
    M.rect(x + 4, y, 7, 6, C.ink)
    M.rect(x + 5, y + 1, 5, 4, C.white)
    M.rect(x + 6, y + 2, 1, 1, C.ink)
    M.rect(x + 9, y + 2, 1, 1, C.ink)
    M.rect(x + 5, y + 7, 5, 7, C.ink2)
    M.rect(x + 3, y + 8 + bob, 2, 6, C.ink2)
    M.rect(x + 10, y + 8 + (1 - bob), 2, 6, C.ink2)
    M.rect(x + 5, y + 14, 2, 4, C.dark)
    M.rect(x + 8, y + 14, 2, 4, C.dark)
    M.rect(x + 2, y + 17, 5, 1, C.dark)
    M.rect(x + 8, y + 17, 5, 1, C.dark)
end

function M.bonus(x, y)
    M.rect(x + 3, y, 5, 11, C.green)
    M.rect(x, y + 3, 11, 5, C.green)
    M.rect(x + 4, y + 1, 3, 9, C.white)
    M.rect(x + 1, y + 4, 9, 3, C.white)
end

function M.hud(score, timeLeft, lives, combo, level, stars, goal)
    M.panel(27, 6, 186, 38)
    E.text(34, 13, "S " .. tostring(score), C.ink)
    E.text(88, 13, "L" .. tostring(level), C.ink2)

    local t = "T " .. tostring(math.max(0, math.ceil(timeLeft)))
    E.text(205 - E.text_width(t), 13, t, C.accent2)

    E.text(34, 28, "HP " .. string.rep("*", math.max(0, lives)), C.green)
    if combo and combo > 1 then
        E.text(90, 28, "COMBO x" .. tostring(combo), C.accent)
    else
        E.text(90, 28, "COMBO x1", C.pencil)
    end

    local p = tostring(stars or 0) .. "/" .. tostring(goal or 0)
    E.text(205 - E.text_width(p), 28, p, C.ink2)
end

function M.progress(x, y, w, value, maximum)
    maximum = math.max(1, maximum or 1)
    local fill = math.floor(w * math.max(0, math.min(maximum, value or 0)) / maximum)
    M.rect(x, y, w, 5, C.shadow)
    M.rect(x, y, fill, 5, C.accent)
    E.frame(x, y, w, 5, C.ink2)
end

return M
