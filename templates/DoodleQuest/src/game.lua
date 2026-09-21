local E = engine
local Gfx = require("src.gfx")
local C = Gfx.C

local M = {}
M.onExit = function() end

local GOAL_STARS = 15
local MAX_LIVES = 3
local state = {}

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function hit(ax, ay, aw, ah, bx, by, bw, bh)
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by
end

local function rnd()
    state.seed = (state.seed * 73 + 41) % 997
    return state.seed / 997
end

local function placeStar()
    state.sx = 38 + math.floor(rnd() * 156)
    state.sy = 58 + math.floor(rnd() * 182)
end

local function placeBonus()
    state.bx = 44 + math.floor(rnd() * 144)
    state.by = 68 + math.floor(rnd() * 164)
    state.bonusOn = true
end

local function resetPlayer()
    state.x = 112
    state.y = 154
end

local function levelForStars(stars)
    return math.min(3, math.floor(stars / 5) + 1)
end

local function syncLevel()
    local nextLevel = levelForStars(state.stars)
    if nextLevel ~= state.level then
        state.level = nextLevel
        state.levelFlash = 1.4
        state.time = math.min(75, state.time + 4)
    end
end

local function resetHazards()
    state.hazards = {
        { x = 40,  y = 88,  w = 25, h = 16, vx = 22,  vy = 0 },
        { x = 152, y = 208, w = 28, h = 16, vx = -26, vy = 0 },
        { x = 80,  y = 150, w = 22, h = 14, vx = 30,  vy = 15 },
        { x = 170, y = 112, w = 20, h = 18, vx = -34, vy = -17 },
    }
end

function M.start()
    state.seed = math.floor(E.tick_ms()) % 997
    state.score = 0
    state.stars = 0
    state.level = 1
    state.time = 60
    state.lives = MAX_LIVES
    state.combo = 1
    state.comboT = 0
    state.invuln = 0
    state.frame = 0
    state.anim = 0
    state.over = false
    state.win = false
    state.paused = false
    state.pauseSel = 1
    state.bonusOn = false
    state.levelFlash = 0
    state.hitFlash = 0
    resetPlayer()
    resetHazards()
    placeStar()
end

local function damagePlayer()
    if state.invuln > 0 or state.over then return end
    state.lives = state.lives - 1
    state.combo = 1
    state.comboT = 0
    state.invuln = 1.2
    state.hitFlash = 0.35
    resetPlayer()
    if state.lives <= 0 then
        state.over = true
        state.win = false
    end
end

local function collectStar()
    if state.comboT > 0 then
        state.combo = math.min(3, state.combo + 1)
    else
        state.combo = 1
    end
    state.comboT = 2.4
    state.score = state.score + state.combo
    state.stars = state.stars + 1

    if state.stars % 4 == 0 and not state.bonusOn then
        placeBonus()
    end

    syncLevel()
    if state.stars >= GOAL_STARS then
        state.win = true
        state.over = true
    else
        placeStar()
    end
end

local function updateHazards(dt)
    local activeCount = math.min(#state.hazards, state.level + 1)
    for i = 1, activeCount do
        local h = state.hazards[i]
        local speedMul = 1 + (state.level - 1) * 0.22
        h.x = h.x + h.vx * speedMul * dt
        h.y = h.y + h.vy * speedMul * dt

        if h.x < 30 then
            h.x = 30
            h.vx = math.abs(h.vx)
        elseif h.x + h.w > 210 then
            h.x = 210 - h.w
            h.vx = -math.abs(h.vx)
        end

        if h.vy ~= 0 then
            if h.y < 60 then
                h.y = 60
                h.vy = math.abs(h.vy)
            elseif h.y + h.h > 250 then
                h.y = 250 - h.h
                h.vy = -math.abs(h.vy)
            end
        end

        if hit(state.x, state.y, 14, 18, h.x, h.y, h.w, h.h) then
            damagePlayer()
        end
    end
end

function M.update(dt)
    if state.paused or state.over then return end

    state.time = state.time - dt
    if state.time <= 0 then
        state.time = 0
        state.over = true
        state.win = false
        return
    end

    if state.comboT > 0 then
        state.comboT = math.max(0, state.comboT - dt)
        if state.comboT <= 0 then state.combo = 1 end
    end
    if state.invuln > 0 then state.invuln = math.max(0, state.invuln - dt) end
    if state.levelFlash > 0 then state.levelFlash = math.max(0, state.levelFlash - dt) end
    if state.hitFlash > 0 then state.hitFlash = math.max(0, state.hitFlash - dt) end

    state.anim = state.anim + dt
    if state.anim > 0.16 then
        state.anim = 0
        state.frame = (state.frame + 1) % 2
    end

    updateHazards(dt)

    if hit(state.x, state.y, 14, 18, state.sx, state.sy, 9, 9) then
        collectStar()
    end

    if state.bonusOn and hit(state.x, state.y, 14, 18, state.bx, state.by, 11, 11) then
        state.bonusOn = false
        state.lives = math.min(MAX_LIVES, state.lives + 1)
        state.time = math.min(75, state.time + 7)
        state.score = state.score + 3
    end
end

local function drawHazard(h, index)
    local wobble = (state.frame + index) % 2
    Gfx.rect(h.x, h.y, h.w, h.h, C.accent2)
    E.frame(math.floor(h.x), math.floor(h.y), h.w, h.h, C.ink)
    Gfx.rect(h.x + 3, h.y + 3 + wobble, h.w - 6, 2, C.white)
    Gfx.rect(h.x + 5, h.y + h.h - 5 - wobble, h.w - 10, 1, C.ink)
end

local function drawPause()
    Gfx.panel(42, 91, 156, 136)
    Gfx.text_center(108, "PAUSED", C.ink)
    Gfx.button(132, "RESUME", state.pauseSel == 1)
    Gfx.button(170, "RESTART", state.pauseSel == 2)
    Gfx.button(208, "MAIN MENU", state.pauseSel == 3)
end

local function drawOver()
    Gfx.panel(42, 104, 156, 110)
    Gfx.text_center(
        120,
        state.win and "QUEST COMPLETE!" or "GAME OVER",
        state.win and C.green or C.accent2
    )
    Gfx.text_center(148, "SCORE " .. tostring(state.score), C.ink)
    Gfx.text_center(170, "STARS " .. tostring(state.stars) .. "/" .. GOAL_STARS, C.ink2)
    Gfx.text_center(194, "5 RETRY / 0 MENU", C.ink2)
end

function M.draw()
    Gfx.paper()
    Gfx.hud(
        state.score,
        state.time,
        state.lives,
        state.combo,
        state.level,
        state.stars,
        GOAL_STARS
    )

    Gfx.panel(27, 49, 186, 218)

    local activeCount = math.min(#state.hazards, state.level + 1)
    for i = 1, activeCount do
        drawHazard(state.hazards[i], i)
    end

    Gfx.star(state.sx, state.sy, C.accent)
    if state.bonusOn then Gfx.bonus(state.bx, state.by) end

    local blink = state.invuln > 0 and math.floor(state.invuln * 10) % 2 == 0
    if not blink then
        Gfx.player(state.x, state.y, state.frame)
    end

    Gfx.progress(36, 253, 168, state.stars, GOAL_STARS)

    if state.levelFlash > 0 then
        Gfx.panel(73, 70, 94, 28)
        Gfx.text_center(80, "LEVEL " .. tostring(state.level), C.accent2)
    elseif state.hitFlash > 0 then
        Gfx.panel(75, 70, 90, 28)
        Gfx.text_center(80, "-1 LIFE", C.accent2)
    end

    if state.paused then
        drawPause()
    elseif state.over then
        drawOver()
    else
        Gfx.text_center(281, "2/4/6/8 MOVE   0 PAUSE", C.ink2)
    end
end

function M.keypressed(k)
    if state.over then
        if k == "ok" then
            M.start()
        elseif k == "back" then
            M.onExit()
        end
        return
    end

    if state.paused then
        if k == "up" then
            state.pauseSel = (state.pauseSel - 2) % 3 + 1
        elseif k == "down" then
            state.pauseSel = state.pauseSel % 3 + 1
        elseif k == "back" then
            state.paused = false
        elseif k == "ok" then
            if state.pauseSel == 1 then
                state.paused = false
            elseif state.pauseSel == 2 then
                M.start()
            else
                M.onExit()
            end
        end
        return
    end

    local step = 9
    if k == "left" then
        state.x = clamp(state.x - step, 31, 196)
    elseif k == "right" then
        state.x = clamp(state.x + step, 31, 196)
    elseif k == "up" then
        state.y = clamp(state.y - step, 53, 240)
    elseif k == "down" then
        state.y = clamp(state.y + step, 53, 240)
    elseif k == "back" then
        state.paused = true
        state.pauseSel = 1
    end
end

function M.keyreleased(_) end

return M
