"""Font icon helpers for the VXPEngine-derived UI chrome.

QtAwesome supplies Font Awesome as a Python dependency, so the project does
not bundle or distribute any font file itself. When Font Awesome cannot be
loaded at runtime, every icon falls back to the system Segoe glyph layer in
``app.ui.icons`` so the chrome never renders empty buttons.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QColor, QIcon

try:
    import qtawesome as qta
except Exception:  # App still opens if QtAwesome was not installed yet.
    qta = None

# Khi qtawesome vắng mặt hoặc font Font Awesome không load được (build đóng
# gói), mọi icon chrome tụt về glyph Segoe MDL2/Fluent của app.ui.icons.
_FA5_TO_GLYPH = {
    "arrow-up": "arrow_up",
    "bell": "bell",
    "book-open": "library",
    "box": "layers",
    "broom": "spark",
    "check": "check",
    "check-circle": "check",
    "circle": "circle",
    "circle-notch": "sync",
    "clone": "duplicate",
    "code-branch": "code",
    "cog": "settings",
    "crop-alt": "cut",
    "desktop": "terminal",
    "download": "download",
    "ellipsis-v": "more",
    "eraser": "edit",
    "exchange-alt": "sync",
    "exclamation-circle": "error",
    "exclamation-triangle": "warning",
    "external-link-alt": "open_external",
    "file": "file",
    "file-alt": "file",
    "file-code": "code",
    "folder": "folder",
    "folder-open": "folder_open",
    "folder-plus": "new_folder",
    "forward": "forward",
    "gamepad": "gamepad",
    "home": "home",
    "image": "image",
    "info-circle": "info",
    "location-arrow": "location",
    "magic": "spark",
    "microchip": "microchip",
    "minus": "minus",
    "music": "music",
    "paint-brush": "brush",
    "palette": "brush",
    "pen": "edit",
    "play": "play",
    "play-circle": "play",
    "plus": "add",
    "power-off": "power",
    "puzzle-piece": "build",
    "robot": "robot",
    "save": "save",
    "search": "search",
    "sign-out-alt": "back",
    "square": "square",
    "stethoscope": "info",
    "stop": "stop",
    "stop-circle": "stop",
    "sync-alt": "sync",
    "terminal": "terminal",
    "th": "grid",
    "times": "close",
    "times-circle": "close",
    "trash-alt": "delete",
    "users": "users",
    "window-minimize": "minus",
    "wrench": "build",
}


def _glyph_fallback(name: str, color: str, color_active: str) -> QIcon:
    from app.ui.icons import font_icon

    key = name.split(".", 1)[-1]
    return font_icon(
        _FA5_TO_GLYPH.get(key, "info"),
        size=16,
        normal=color or "#9CA2BB",
        active=color_active or "#FFFFFF",
        disabled="#5D637C",
    )


def _usable(ic: QIcon) -> bool:
    return not ic.isNull() and not ic.pixmap(16, 16).isNull()


@lru_cache(maxsize=256)
def _cached_icon(name: str, color: str, color_active: str) -> QIcon:
    if qta is not None:
        try:
            options = {}
            if color:
                options["color"] = QColor(color)
            if color_active:
                options["color_active"] = QColor(color_active)
            result = qta.icon(name, **options)
            if _usable(result):
                return result
        except Exception:
            pass
    return _glyph_fallback(name, color, color_active)


def icon(name: str, color: str = "#9CA2BB", color_active: str = "#FFFFFF") -> QIcon:
    """Return a Font Awesome icon, falling back to a Segoe UI glyph."""
    return _cached_icon(name, color, color_active)


@lru_cache(maxsize=8)
def _cached_app_icon(preferred: str | None) -> QIcon:
    candidates: list[Path] = []
    if preferred:
        candidates.append(Path(preferred).expanduser())
    from_env = os.environ.get("LUAS30_APP_ICON")
    if from_env:
        candidates.append(Path(from_env).expanduser())
    for candidate in candidates:
        for path in (candidate, candidate.with_suffix(".ico"), candidate.with_suffix(".png")):
            if path.is_file():
                result = QIcon(str(path))
                if not result.isNull():
                    return result
    return icon("fa5s.gamepad", "#64A7FF")


def app_icon(preferred: str | None = None) -> QIcon:
    """Return the application icon.

    Resolution order: the explicit ``preferred`` path, the ``LUAS30_APP_ICON``
    environment variable, then the QtAwesome gamepad glyph.
    """
    return _cached_app_icon(str(preferred) if preferred else None)
