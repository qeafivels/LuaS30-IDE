local E = engine
local Gfx = require("src.gfx")
local C = Gfx.C

local M = {}
M.show = "splash"
M.go = function(_) end

local elapsed = 0
local menu = 1
local settings = 1
local sound = true

local MENU = { "PLAY", "HOW TO PLAY", "SETTINGS", "ABOUT", "EXIT" }

function M.enter(name)
    M.show = name
    if name == "splash" then elapsed = 0 end
    if name == "menu" then menu = 1 end
    if name == "settings" then settings = 1 end
end

function M.update(dt)
    elapsed = elapsed + dt
    if M.show == "splash" and elapsed > 2.8 then
        M.go("menu")
    end
end

local function footer(text)
    Gfx.panel(34, 282, 172, 24)
    Gfx.text_center(291, text, C.ink2)
end

local function drawSplash()
    Gfx.paper()
    Gfx.panel(32, 78, 176, 122)
    Gfx.text_center(96, "DOODLE QUEST", C.ink)
    Gfx.text_center(116, "NOTEBOOK ADVENTURE", C.accent2)
    Gfx.player(110, 142, math.floor(elapsed * 5))
    Gfx.star(70, 150, C.accent)
    Gfx.star(160, 132, C.green)
    if math.floor(elapsed * 2) % 2 == 0 then
        Gfx.text_center(224, "PRESS 5", C.ink2)
    end
    footer("LUA S30 GAME TEMPLATE")
end

local function drawMenu()
    Gfx.paper()
    Gfx.title("DOODLE QUEST")
    for i = 1, #MENU do
        Gfx.button(58 + (i - 1) * 39, MENU[i], i == menu)
    end
    footer("2/8 SELECT   5 OK")
end

local function drawGuide()
    Gfx.paper()
    Gfx.title("HOW TO PLAY")
    Gfx.panel(30, 58, 180, 178)
    local lines = {
        "MOVE: 2 4 6 8",
        "COLLECT 15 ORANGE STARS",
        "CHAIN STARS FOR x3 COMBO",
        "GREEN + = LIFE / TIME BONUS",
        "0 / BACK: PAUSE MENU",
    }
    for i = 1, #lines do
        E.text(42, 78 + (i - 1) * 28, lines[i], i == 1 and C.accent2 or C.ink)
    end
    footer("5 / BACK TO MENU")
end

local function drawSettings()
    Gfx.paper()
    Gfx.title("SETTINGS")
    Gfx.panel(30, 68, 180, 118)
    Gfx.button(86, "SOUND: " .. (sound and "ON" or "OFF"), settings == 1)
    Gfx.button(128, "RESET DEFAULTS", settings == 2)
    footer("2/8 SELECT   5 CHANGE")
end

local function drawAbout()
    Gfx.paper()
    Gfx.title("ABOUT")
    Gfx.panel(28, 62, 184, 150)
    Gfx.text_center(82, "DOODLE QUEST", C.ink)
    Gfx.text_center(106, "UI + GAME TEMPLATE", C.accent2)
    Gfx.text_center(132, "3 LEVELS / COMBO / LIVES", C.ink2)
    Gfx.text_center(158, "LOW-RAM PROCEDURAL ART", C.ink2)
    Gfx.text_center(184, "240x320 / MTK6260", C.green)
    footer("5 / BACK TO MENU")
end

function M.draw()
    if M.show == "splash" then drawSplash()
    elseif M.show == "menu" then drawMenu()
    elseif M.show == "guide" then drawGuide()
    elseif M.show == "settings" then drawSettings()
    else drawAbout() end
end

function M.keypressed(k)
    if M.show == "splash" then
        M.go("menu")
        return
    end

    if M.show == "menu" then
        if k == "up" then menu = (menu - 2) % #MENU + 1
        elseif k == "down" then menu = menu % #MENU + 1
        elseif k == "ok" then
            if menu == 1 then M.go("play")
            elseif menu == 2 then M.go("guide")
            elseif menu == 3 then M.go("settings")
            elseif menu == 4 then M.go("about")
            else E.exit() end
        elseif k == "back" then
            E.exit()
        end
        return
    end

    if M.show == "settings" then
        if k == "up" then settings = (settings - 2) % 2 + 1
        elseif k == "down" then settings = settings % 2 + 1
        elseif k == "ok" then
            if settings == 1 then sound = not sound else sound = true end
        elseif k == "back" then M.go("menu") end
        return
    end

    if k == "back" or k == "ok" then
        M.go("menu")
    end
end

return M
