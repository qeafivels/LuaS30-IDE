-- Doodle Quest: lightweight notebook-art game template for LuaS30 / MRE.
-- Screens: splash -> main menu -> play -> pause, plus guide/settings/about.

local E = engine
local Gfx = require("src.gfx")
local UI = require("src.ui")
local Game = require("src.game")

local mode = "ui"

local KEYMAP = {
    ["2"] = "up", ["8"] = "down", ["4"] = "left", ["6"] = "right",
    ["5"] = "ok", ["#"] = "ok",
    ["0"] = "back", ["clear"] = "back", ["back"] = "back",
    ["softleft"] = "back", ["softright"] = "ok",
}

local function route(name)
    if name == "play" then
        mode = "game"
        Game.start()
    else
        mode = "ui"
        UI.enter(name)
    end
end

function E.load()
    E.set_font(8)
    UI.go = route
    Game.onExit = function() route("menu") end
    route("splash")
end

function E.update(dt)
    if mode == "game" then Game.update(dt) else UI.update(dt) end
end

function E.draw()
    if mode == "game" then Game.draw() else UI.draw() end
    E.flush()
end

function E.keypressed(key)
    local k = KEYMAP[key] or key
    if mode == "game" then Game.keypressed(k) else UI.keypressed(k) end
end

function E.keyreleased(key)
    local k = KEYMAP[key] or key
    if mode == "game" then Game.keyreleased(k) end
end
