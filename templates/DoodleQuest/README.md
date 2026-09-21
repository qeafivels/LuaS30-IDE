# Doodle Quest — LuaS30 game template

A lightweight 240×320 starter game with procedural notebook/doodle graphics, complete keypad UI, and a small but expandable gameplay loop.

## Included screens

- Splash
- Main menu
- How To Play
- Settings
- About
- Gameplay HUD
- Pause menu
- Win / Game Over state

## Gameplay sample

- 3 difficulty levels that unlock as stars are collected
- 15-star objective
- Score + x1/x2/x3 combo chain
- 3 lives with short post-hit invulnerability
- Moving doodle/ink hazards
- Green bonus pickup that restores life and adds time
- Progress bar, level popup, hit feedback
- Pause / Resume / Restart / Main Menu flow

## Controls

- 2 / 8: up / down
- 4 / 6: left / right
- 5 or #: confirm
- 0 / Back / Soft Left: pause / back

## Create from LuaS30 IDE

Open **New Project**, choose **Doodle Quest** in the **Mẫu dự án** field, then configure APPNAME, chipset, resolution and heap. The IDE copies this template, generates a unique AppID and opens the new project.

## Target

- Nokia S30+ / MediaTek MRE
- MTK6260
- 240×320
- 1024 KB baseline heap
- 15 FPS
- profile: `nokia225-rm1011`

The graphics are drawn with rectangles, frames and text, so the template does not depend on large bitmap assets and remains suitable as a low-RAM starter project.
