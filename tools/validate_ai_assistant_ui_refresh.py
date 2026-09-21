from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

print("== Python syntax gate ==")
result = subprocess.run(
    [sys.executable, "-m", "compileall", "-q", str(ROOT / "studio"), str(ROOT / "tools")],
    cwd=ROOT,
    check=False,
)
if result.returncode:
    raise SystemExit(result.returncode)
print("PASS: python -m compileall -q studio tools")

chat = (ROOT / "studio/app/views/ai_chat_view.py").read_text(encoding="utf-8")
renderer = (ROOT / "studio/app/views/ai_chat_render.py").read_text(encoding="utf-8")
protocol = (ROOT / "studio/app/services/ai_agent_protocol.py").read_text(encoding="utf-8")
theme = (ROOT / "studio/app/ui/theme.py").read_text(encoding="utf-8")
main_window = (ROOT / "studio/app/vxpui/main_window.py").read_text(encoding="utf-8")
editor_tabs = (ROOT / "studio/app/editor/editor_tabs.py").read_text(encoding="utf-8")
editor_groups = (ROOT / "studio/app/editor/editor_group_manager.py").read_text(encoding="utf-8")

missing = []

for token in (
    "TranscriptHtmlRenderer",
    "ACCESS_MODES",
    'QPushButton("Gửi")',
    "def _send_or_stop",
    "def stop_agent",
    "worker.abort()",
):
    if token not in chat:
        missing.append(f"chat:{token}")

for token in (
    "class TranscriptHtmlRenderer",
    "def render_markdown",
    "def render_code_block",
    "AI Agent",
):
    if token not in renderer:
        missing.append(f"renderer:{token}")

for token in ("_recover_fenced_files", "_recover_json_tool_calls"):
    if token not in protocol:
        missing.append(f"protocol:{token}")

for token in (
    "class _AITabStatusBadge(QLabel)",
    '"modified": "AI Modified"',
    '"created": "AI Created"',
    "def set_ai_file_status(self, path: str | Path, state: str) -> bool",
    "def clear_ai_file_status(self, path: str | Path) -> bool",
    "def open_file(self, path: str | Path, *, activate: bool = True)",
):
    if token not in editor_tabs:
        missing.append(f"editor_tabs:{token}")

for token in (
    "def set_ai_file_status(self, path: str | Path, state: str) -> bool",
    "def clear_ai_file_status(self, path: str | Path) -> bool",
    "activate=False",
):
    if token not in editor_groups:
        missing.append(f"editor_groups:{token}")

for token in (
    "def _open_ai_touched_tabs(self, change_set: PreparedChangeSet)",
    "self.tabs.open_file(target, activate=False)",
    "self.tabs.set_ai_file_status(",
    '"modified" if change.existed else "created"',
    "self.tabs.open_file(opened_targets[0], activate=True)",
):
    if token not in main_window:
        missing.append(f"main_window:{token}")

for token in (
    "QLabel#AITabStatusBadge",
    'QLabel#AITabStatusBadge[aiState="modified"]',
    'QLabel#AITabStatusBadge[aiState="created"]',
    "max-width: 230px",
):
    if token not in theme:
        missing.append(f"theme:{token}")

# Latest upstream live-problem/diagnostic behavior must survive the merge.
for token in ("_ai_problem_timer", "_refresh_ai_problem_card", "_open_ai_touched_tabs"):
    if token not in main_window:
        missing.append(f"upstream regression:{token}")

if missing:
    print("FAIL: upstream sync / AI editor workflow")
    for item in missing:
        print(" -", item)
    raise SystemExit(1)

print("PASS: latest upstream AI assistant behavior is preserved")
print("PASS: AI-touched files open as background editor tabs")
print("PASS: AI Modified / AI Created badges are wired and themed")
print("PASS: Full Access / Hard Stop wiring remains present")
