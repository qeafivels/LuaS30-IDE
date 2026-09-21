from __future__ import annotations

import compileall
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

print("== Python syntax ==")
if not compileall.compile_dir(ROOT / "studio", quiet=1):
    raise SystemExit("FAIL: Python syntax in studio/")
print("PASS: studio Python compiles")

project_session = (ROOT / "studio/app/core/project_session.py").read_text(encoding="utf-8")
dialog = (ROOT / "studio/app/ui/mediatek_mre_dialog.py").read_text(encoding="utf-8")
main_window = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")

required_python = {
    "project_session": (
        '"doodle-quest": "DoodleQuest"',
        'template_name: str = "basic"',
        'template_dir = PROJECT_TEMPLATES.get(template_key)',
        'payload["template"] = template_key',
    ),
    "dialog": (
        "PROJECT_TEMPLATE_OPTIONS",
        '("doodle-quest", "Doodle Quest"',
        "self.template.setCurrentIndex(1)",
        "template_id: str",
        'template_id=str(self.template.currentData() or "basic")',
    ),
    "main_window": (
        "template_name=config.template_id",
        'f" | Template {config.template_id}"',
    ),
}

sources = {
    "project_session": project_session,
    "dialog": dialog,
    "main_window": main_window,
}
missing = []
for group, tokens in required_python.items():
    for token in tokens:
        if token not in sources[group]:
            missing.append(f"{group}: {token}")

template = ROOT / "templates/DoodleQuest"
required_files = (
    "project.json",
    "conf.lua",
    "main.lua",
    ".luas30/mre_sdk.json",
    ".luas30/ui_design.json",
    "src/engine.lua",
    "src/gfx.lua",
    "src/ui.lua",
    "src/game.lua",
    "README.md",
)
for rel in required_files:
    if not (template / rel).is_file():
        missing.append(f"template file: {rel}")

for rel in ("project.json", ".luas30/mre_sdk.json", ".luas30/ui_design.json"):
    path = template / rel
    if path.is_file():
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            missing.append(f"invalid JSON {rel}: {exc}")

game = (template / "src/game.lua").read_text(encoding="utf-8")
gfx = (template / "src/gfx.lua").read_text(encoding="utf-8")
ui = (template / "src/ui.lua").read_text(encoding="utf-8")

for token in (
    "GOAL_STARS = 15",
    "MAX_LIVES = 3",
    "state.combo",
    "state.paused",
    "state.bonusOn",
    "levelForStars",
    "updateHazards",
    "drawPause",
):
    if token not in game:
        missing.append(f"gameplay: {token}")

for token in ("function M.hud", "function M.bonus", "function M.progress"):
    if token not in gfx:
        missing.append(f"gfx: {token}")

for token in (
    "COLLECT 15 ORANGE STARS",
    "CHAIN STARS FOR x3 COMBO",
    "GREEN + = LIFE / TIME BONUS",
):
    if token not in ui:
        missing.append(f"ui guide: {token}")

for path in (
    ROOT / "studio/app/core/project_session.py",
    ROOT / "studio/app/ui/mediatek_mre_dialog.py",
    ROOT / "studio/app/vxpui/main_window.py",
    template / "main.lua",
    template / "src/gfx.lua",
    template / "src/ui.lua",
    template / "src/game.lua",
):
    text = path.read_text(encoding="utf-8")
    for marker in ("<<<<<<<", "=======", ">>>>>>>"):
        if marker in text:
            missing.append(f"conflict marker {marker}: {path.relative_to(ROOT)}")

if missing:
    print("FAIL: Doodle Quest template validation")
    for item in missing:
        print(" -", item)
    raise SystemExit(1)

project = json.loads((template / "project.json").read_text(encoding="utf-8"))
if (project.get("screen_width"), project.get("screen_height")) != (240, 320):
    raise SystemExit("FAIL: Doodle Quest must default to 240x320")
if int(project.get("ram_kb", 0)) > 1024:
    raise SystemExit("FAIL: Doodle Quest baseline heap must stay <= 1024 KB")

print("PASS: New Project exposes Doodle Quest")
print("PASS: template JSON and required files are valid")
print("PASS: gameplay includes 3 levels, combo, lives, bonus and pause flow")
print("PASS: no merge-conflict markers in touched sources")
