#!/usr/bin/env python3
"""
studio_theme_check.py — Kiểm tra bảng màu + render offscreen toàn Studio.

Chạy:

    QT_QPA_PLATFORM=offscreen QT_QPA_FONTDIR="C:/Windows/Fonts" \
        py -3.12 -u tools/studio_theme_check.py
    ... tools/studio_theme_check.py --shots build/theme-shots

Ba nhóm kiểm tra:

  A. Tĩnh — bảng màu
     * `theme.py` không còn hex trực tiếp, mọi màu là token `@TEN`.
     * `APP_STYLE` giải ra được, không sót token nào.
     * Bo góc chỉ còn bốn mức 6 / 8 / 10 / 12px (10 = thẻ lớn + nút Gửi của
       panel AI Agent theo bảng màu UAGet Desktop).
     * Không còn `color: white|black`.
     * Mọi hex trong `studio/**/*.py` phải nằm trong `palette.py`, trừ những
       file có trong ALLOWLIST (màu cú pháp, bảng màu nội dung game, swatch).

  B. Tĩnh — tương phản WCAG của các cặp chữ/nền chính.

  C. Render — dựng thật `MainWindow` + hộp thoại "Cấu hình MediaTek MRE SDK"
     bằng nền offscreen, quét khối sáng (rò theme sáng) và kiểm hình học.
     Chạy trong `LUAS30_APPDATA` tạm nên KHÔNG đụng config thật của người dùng.

`QT_QPA_FONTDIR` là BẮT BUỘC: thiếu nó Qt nạp 0 font, glyph thành ô vuông mà
ảnh vẫn lưu được nên lỗi xảy ra âm thầm.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "studio"
sys.path.insert(0, str(STUDIO))

# File được phép dùng màu ngoài palette — kèm lý do, để không ai "dọn" nhầm.
ALLOWLIST: dict[str, str] = {
    "app/editor/lua_highlighter.py":
        "màu cú pháp Lua — bảng riêng, cố ý không theo chrome",
    "app/views/ui_designer/lua_export.py":
        "bảng màu NỘI DUNG game, sinh vào ui_design.lua",
    "app/views/ui_designer/items.py":
        "xem trước nội dung widget trong khung 240x320 (khớp lua_export.py)",
    "app/views/ui_designer/color_button.py":
        "danh sách swatch + màu mặc định của color picker — DỮ LIỆU, không phải chrome",
    "app/views/ui_designer/properties_panel.py":
        "DEFAULT_FILL là màu NỘI DUNG của thành phần mới (ghi vào ui_design.json)",
    "app/views/ui_designer/design_store.py":
        "ví dụ JSON trong docstring",
    "app/services/ai_agent_protocol.py":
        "ví dụ JSON gửi cho model — màu NỘI DUNG game (khớp lua_export.ACCENT), không phải chrome",
    "app/widgets/vxp_emu_window.py":
        "bezel + màn Nokia 225 của cửa sổ giả lập — ART THIẾT BỊ, không phải chrome IDE",
}

# Chrome VXPEngine (studio/app/vxpui) đã ĐỒNG BỘ theo bảng màu UAGet Desktop
# (#111122/#19192e/#ff8a00…) — vẫn giữ nguồn riêng là dark_theme.qss (hex trực
# tiếp, có chủ ý) nên nằm ngoài palette.py của Studio.
for _chrome in (
    "code_editor", "custom_dialog", "home_page", "icons", "log_format",
    "main_window", "panel_frame", "task_progress", "title_bar", "toast",
    "vxpemu_panel",
):
    ALLOWLIST[f"app/vxpui/{_chrome}.py"] = (
        "bảng màu chrome VXPEngine — port 1:1, nguồn là dark_theme.qss"
    )

FAILS: list[str] = []


def check(label: str, cond: bool, extra: str = "") -> bool:
    if not cond:
        FAILS.append(label)
    print(f"  [{'OK  ' if cond else 'FAIL'}] {label} {extra}", flush=True)
    return bool(cond)


def hexes(text: str) -> list[str]:
    return [m.lower() for m in re.findall(r"#[0-9a-fA-F]{6}\b", text)]


# ---------------------------------------------------------------- A. bảng màu

def check_palette() -> None:
    from app.ui import palette
    from app.ui.theme import APP_STYLE

    print("\n-- A. bảng màu --", flush=True)

    raw = (STUDIO / "app/ui/theme.py").read_text(encoding="utf-8")
    body = raw.split('APP_STYLE = _substitute(r"""', 1)[1]
    check("theme.py không còn hex trực tiếp", not hexes(body),
          f"còn {sorted(set(hexes(body)))[:5]}")

    leftover = re.findall(r"@[A-Z][A-Z0-9_]*", APP_STYLE)
    check("APP_STYLE giải hết token", not leftover, f"sót={leftover[:5]}")

    radii = sorted({int(r) for r in re.findall(r"border-radius: (\d+)px", APP_STYLE)})
    check("bo góc chỉ còn 6/8/10/12px", set(radii) <= {6, 8, 10, 12}, f"radii={radii}")

    check("không còn 'color: white|black'",
          not re.search(r"color:\s*(?:white|black)\b", APP_STYLE))

    allowed = palette.hex_set()
    strays: dict[str, list[str]] = {}
    for path in sorted((STUDIO).rglob("*.py")):
        rel = path.relative_to(STUDIO).as_posix()
        if rel in ALLOWLIST:
            continue
        bad = sorted(set(h for h in hexes(path.read_text(encoding="utf-8"))
                         if h not in allowed))
        if bad:
            strays[rel] = bad
    check("mọi màu chrome đều nằm trong palette.py", not strays, f"lạ={strays}")

    # token khai báo mà không ai dùng -> dấu hiệu palette phình ra vô ích
    used = set(hexes(APP_STYLE))
    for path in (STUDIO).rglob("*.py"):
        used.update(hexes(path.read_text(encoding="utf-8")))
    unused = sorted(name for name, value in palette.values().items()
                    if value.lower() not in used)
    print(f"  [note] token chưa dùng ở đâu: {unused or 'không có'}", flush=True)


# ---------------------------------------------------------------- B. tương phản

def _lum(color: str) -> float:
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(fg: str, bg: str) -> float:
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast() -> None:
    from app.ui import palette as P

    print("\n-- B. tương phản WCAG --", flush=True)
    pairs = [
        ("chữ thường trên panel", P.TEXT_2, P.BG_SURFACE, 4.5),
        ("chữ thường trên nền lõm", P.TEXT_2, P.BG_INK, 4.5),
        ("tiêu đề trên panel", P.TEXT, P.BG_SURFACE, 4.5),
        ("nhãn mờ trên panel", P.TEXT_4, P.BG_SURFACE, 4.5),
        ("nhãn mờ trên nền lõm", P.TEXT_4, P.BG_INK, 4.5),
        ("ghi chú nhỏ trên nền lõm", P.TEXT_5, P.BG_INK, 4.5),
        ("chữ trên nút accent", P.ON_ACCENT, P.ACCENT, 4.5),
        ("chữ trên nút accent hover", P.ON_ACCENT, P.ACCENT_HOVER, 4.5),
        ("chữ trên nút thành công", P.ON_ACCENT, P.GREEN, 4.5),
        ("chữ trên mục đang chọn", P.TEXT, P.BG_SELECT, 4.5),
        ("lỗi trên panel", P.RED, P.BG_SURFACE, 4.5),
        ("cảnh báo trên panel", P.AMBER, P.BG_SURFACE, 4.5),
        ("thành công trên panel", P.GREEN_LIGHT, P.BG_SURFACE, 4.5),
        ("info trên panel", P.INFO, P.BG_SURFACE, 4.5),
    ]
    for label, fg, bg, minimum in pairs:
        ratio = contrast(fg, bg)
        check(f"{label} {fg} / {bg} >= {minimum}", ratio >= minimum,
              f"{ratio:.2f}")


# ---------------------------------------------------------------- C. render

def light_blocks(pixmap, block: int = 24, threshold: float = 150.0, ignore=()):
    """Trả về các khối 24px SÁNG đều (rò theme sáng vào UI tối).

    `ignore` là danh sách QRect theo toạ độ LOGIC (hình học widget) — dùng cho
    những vùng SÁNG CÓ CHỦ Ý (nút accent cam). Khai báo vùng miễn trừ, đừng nới
    ngưỡng: nới ngưỡng là bịt luôn khả năng phát hiện rò theme thật.

    `widget.grab()` trả pixmap ở ĐỘ PHÂN GIẢI THIẾT BỊ: trên màn hình scale 125%
    `devicePixelRatio()` = 1.25 nên pixmap lớn hơn widget 1.25 lần. Vì vậy cả ô
    quét lẫn vùng miễn trừ đều được quy đổi sang pixel thiết bị trước khi so —
    nếu không, `ignore` (toạ độ logic) sẽ lệch khỏi vùng sáng thật và sinh FAIL
    GIẢ. Đây là lỗi chỉ lộ ra khi chạy KHÔNG có `QT_QPA_PLATFORM=offscreen`.
    """
    image = pixmap.toImage()
    from PySide6.QtCore import QRect

    dpr = pixmap.devicePixelRatio() or 1.0
    cell_size = max(1, round(block * dpr))
    device_ignore = [
        QRect(round(r.left() * dpr), round(r.top() * dpr),
              round(r.width() * dpr), round(r.height() * dpr))
        for r in ignore
    ]

    hits = []
    for by in range(0, pixmap.height(), cell_size):
        for bx in range(0, pixmap.width(), cell_size):
            cell = QRect(bx, by, cell_size, cell_size)
            if any(cell.intersects(rect) for rect in device_ignore):
                continue
            values = []
            for y in range(by, min(by + cell_size, pixmap.height()), 4):
                for x in range(bx, min(bx + cell_size, pixmap.width()), 4):
                    c = image.pixelColor(x, y)
                    values.append(0.299 * c.red() + 0.587 * c.green()
                                  + 0.114 * c.blue())
            if values and sum(values) / len(values) > threshold and min(values) > 140:
                # báo theo toạ độ LOGIC để thông báo đọc được trên mọi màn hình
                hits.append((round(bx / dpr), round(by / dpr)))
    return hits


def light_bands(pixmap, min_run: int = 64, min_height: int = 3,
                threshold: float = 200.0, ignore=()):
    """Dải SÁNG nằm ngang — bắt vết rò mà `light_blocks` bỏ sót.

    `light_blocks` chỉ báo khi có một khối 24px SÁNG TRỌN VẸN. Một vùng sáng
    MỎNG HƠN thế thì lọt lưới hoàn toàn: hàng tiêu đề `QHeaderView` chỉ cao
    ~29px và bị đường viền cắt trên/dưới, nên không khối 24px nào nằm trọn
    trong đó. Dải trắng bên phải tiêu đề Project Hub đã lọt đúng như vậy và chỉ
    được phát hiện bằng mắt. Hàm này quét theo TỪNG HÀNG và tìm vệt sáng dài
    liên tục, nên bắt được cả vùng mỏng.

    `min_height=3` là CỐ Ý, không phải nới ngưỡng cho dễ qua: backend offscreen
    vẽ một đường 1px ở mép trên thanh tab, còn nền tảng windows thật thì không
    (đã đối chiếu cùng một widget: offscreen `#ffffff`, native `#07101f`). Đường
    1px ấy là artefact của offscreen, không nhìn thấy được, nên không tính là rò
    theme — nhưng vùng sáng cao từ 3px trở lên thì phải báo.

    `min_run=64` chứ không phải 150: sau khi Project Hub có cây thư mục, bảng hẹp
    lại nên vùng tiêu đề trống chỉ còn ~77px. Để ngưỡng 150 thì guard bỏ sót
    đúng cái lỗi nó sinh ra để bắt (đã đo: bỏ rule `QHeaderView` ra, dải rộng
    77px và guard im lặng). Đây là lý do phải chạy phép thử ÂM mỗi khi chỉnh
    ngưỡng: một guard không bắt được lỗi đã biết thì vô dụng.
    """
    image = pixmap.toImage()
    width, height = pixmap.width(), pixmap.height()
    dpr = pixmap.devicePixelRatio() or 1.0
    run_px = max(1, round(min_run * dpr))

    # Vùng miễn trừ quy về pixel thiết bị, theo từng hàng cho nhanh.
    ignored: dict[int, list[tuple[int, int]]] = {}
    for rect in ignore:
        left = max(0, round(rect.left() * dpr))
        right = min(width - 1, round((rect.left() + rect.width()) * dpr))
        top = max(0, round(rect.top() * dpr))
        bottom = min(height - 1, round((rect.top() + rect.height()) * dpr))
        for y in range(top, bottom + 1):
            ignored.setdefault(y, []).append((left, right))

    lit_rows: list[tuple[int, int, int]] = []
    for y in range(height):
        spans = ignored.get(y)
        best = best_start = current = start = 0
        for x in range(width):
            pixel = image.pixel(x, y)
            value = (0.299 * ((pixel >> 16) & 0xFF)
                     + 0.587 * ((pixel >> 8) & 0xFF)
                     + 0.114 * (pixel & 0xFF))
            if value > threshold and not (
                    spans and any(lo <= x <= hi for lo, hi in spans)):
                if current == 0:
                    start = x
                current += 1
                if current > best:
                    best, best_start = current, start
            else:
                current = 0
        if best >= run_px:
            lit_rows.append((y, best_start, best))

    # gộp các hàng liền nhau thành dải
    bands: list[list[int]] = []
    for y, x0, length in lit_rows:
        if bands and y == bands[-1][0] + bands[-1][3]:
            band = bands[-1]
            band[1] = min(band[1], x0)
            band[2] = max(band[2], length)
            band[3] += 1
        else:
            bands.append([y, x0, length, 1])

    min_h = max(1, round(min_height * dpr))
    return [(round(x0 / dpr), round(y / dpr), round(length / dpr), band_h)
            for y, x0, length, band_h in bands if band_h >= min_h]


def qt_close_red(pixmap, rect=None) -> int:
    """Đếm pixel của pixmap X ĐỎ mặc định Qt (`QStyle::SP_TabCloseButton`).

    Lọc theo `r-g` lớn để KHÔNG bắt nhầm màu accent cam (#f59e0b có green=158).
    """
    image = pixmap.toImage()
    x0 = y0 = 0
    x1, y1 = pixmap.width(), pixmap.height()
    if rect is not None:
        x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
    count = 0
    for y in range(max(0, y0), min(y1, pixmap.height())):
        for x in range(max(0, x0), min(x1, pixmap.width())):
            c = image.pixelColor(x, y)
            if c.red() > 150 and c.green() < 120 and c.blue() < 120 \
                    and c.red() - c.green() > 90:
                count += 1
    return count


def check_ai_tab_badges(app, out_dir: Path | None) -> None:
    """AI Created / AI Modified: không bị cắt và không làm tab phình quá rộng."""
    from PySide6.QtWidgets import QTabBar

    from app.editor.editor_tabs import EditorTabs, _AITabStatusBadge

    print("\n-- D. badge tệp do AI thay đổi --", flush=True)

    tmp = Path(tempfile.mkdtemp(prefix="luas30_ai_tabs_"))
    modified = tmp / "player_controller.lua"
    created = tmp / "boss_combo.lua"
    modified.write_text("return {}\n", encoding="utf-8")
    created.write_text("return {}\n", encoding="utf-8")

    tabs = EditorTabs()
    tabs.resize(720, 220)
    tabs.show()
    tabs.ensurePolished()

    tabs.open_file(modified)
    tabs.open_file(created)
    tabs.set_ai_file_status(modified, "modified")
    tabs.set_ai_file_status(created, "created")
    app.processEvents()

    bar = tabs.tabBar()
    expected = (
        (modified, "AI Modified", "modified"),
        (created, "AI Created", "created"),
    )
    for path, label, state in expected:
        found = tabs.find_editor(path)
        check(f"{label}: tìm thấy tab", found is not None)
        if not found:
            continue

        index, _editor = found
        badge = bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
        check(
            f"{label}: dùng _AITabStatusBadge",
            isinstance(badge, _AITabStatusBadge),
            f"type={type(badge).__name__ if badge else 'None'}",
        )
        if not isinstance(badge, _AITabStatusBadge):
            continue

        check(
            f"{label}: đúng text",
            badge.text() == label,
            f"text={badge.text()!r}",
        )
        check(
            f"{label}: đúng state",
            badge.property("aiState") == state,
            f"state={badge.property('aiState')!r}",
        )

        hint = badge.sizeHint()
        check(
            f"{label}: badge không bị cắt ngang",
            badge.width() >= hint.width(),
            f"w={badge.width()} hint={hint.width()}",
        )
        check(
            f"{label}: badge không bị cắt dọc",
            badge.height() >= hint.height(),
            f"h={badge.height()} hint={hint.height()}",
        )

        rect = bar.tabRect(index)
        check(
            f"{label}: tab không rộng quá 240px",
            rect.width() <= 240,
            f"tab_w={rect.width()}",
        )
        check(
            f"{label}: badge nằm trong chiều cao tab",
            badge.height() <= rect.height(),
            f"badge_h={badge.height()} tab_h={rect.height()}",
        )

        close_button = bar.tabButton(index, QTabBar.ButtonPosition.RightSide)
        check(
            f"{label}: vẫn giữ nút đóng tab",
            close_button is not None,
        )
        check(
            f"{label}: tooltip có trạng thái AI",
            label in tabs.tabToolTip(index),
            f"tooltip={tabs.tabToolTip(index)!r}",
        )

    shot = tabs.grab()
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        shot.save(str(out_dir / "ai_file_badges.png"))

    tabs.close()
    shutil = __import__("shutil")
    shutil.rmtree(tmp, ignore_errors=True)


def check_tab_close(app, out_dir: Path | None) -> None:
    """Nút đóng tab: phải là nút của Studio và phải ĐÓNG ĐƯỢC tab."""
    from PySide6.QtWidgets import QLabel, QTabBar

    from app.editor.editor_tabs import EditorTabs, _TabCloseButton

    print("\n-- D. nút đóng tab --", flush=True)

    tabs = EditorTabs()
    tabs.addTab(QLabel("a"), "a")
    tabs.addTab(QLabel("b"), "b")
    tabs.resize(420, 220)
    tabs.show()
    tabs.ensurePolished()
    app.processEvents()

    bar = tabs.tabBar()
    button = bar.tabButton(0, QTabBar.ButtonPosition.RightSide)
    check("nút đóng tab là nút của Studio (không phải pixmap Qt)",
          isinstance(button, _TabCloseButton),
          f"type={type(button).__name__}")

    pixmap = tabs.grab()
    if out_dir:
        pixmap.save(str(out_dir / "tabs.png"))
    check("không còn pixel X đỏ mặc định của Qt",
          qt_close_red(pixmap) == 0, f"n={qt_close_red(pixmap)}")

    before = tabs.count()
    if isinstance(button, _TabCloseButton):
        button.click()
        app.processEvents()
    check("bấm nút đóng -> đóng đúng một tab",
          tabs.count() == before - 1, f"{before} -> {tabs.count()}")
    tabs.close()


def render(out_dir: Path | None) -> None:
    from PySide6.QtCore import QPoint, QRect, QTimer
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication, QPushButton, QWidget

    from app.vxpui.main_window import VxpMainWindow
    from app.ui.mediatek_mre_dialog import MediaTekMREConfigDialog
    from app.ui.theme import APP_STYLE

    print("\n-- C. render offscreen --", flush=True)

    app = QApplication.instance() or QApplication(sys.argv)
    qss = STUDIO / "app/vxpui/resources/dark_theme.qss"
    try:
        app.setStyleSheet(APP_STYLE + "\n" + qss.read_text(encoding="utf-8"))
    except OSError:
        app.setStyleSheet(APP_STYLE)

    check("nạp được font hệ thống (cần QT_QPA_FONTDIR)",
          len(QFontDatabase.families()) > 0,
          f"families={len(QFontDatabase.families())}")

    # SetupDialog lần đầu chạy bằng dialog.exec() — chặn vô hạn trong offscreen;
    # sandbox LUAS30_APPDATA luôn coi là first-run nên phải tắt.
    VxpMainWindow._maybe_first_run_setup = lambda self: None
    window = VxpMainWindow(engine_root=ROOT)
    window.resize(1440, 860)
    window.show()
    window.ensurePolished()
    app.processEvents()

    shots = []

    def grab(widget, name: str):
        pixmap = widget.grab()
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / name
            pixmap.save(str(path))
            shots.append(path)
        return pixmap

    shot = grab(window, "main_window.png")
    # Nút accent "PrimaryAction" SÁNG CÓ CHỦ Ý (cam #FF8A00 của chrome
    # VXPEngine) — miễn trừ đúng vùng của nó, giống hộp thoại MRE bên dưới.
    accent_ignore = []
    for b in window.findChildren(QPushButton):
        if b.objectName() == "PrimaryAction" and b.isVisible():
            top_left = b.mapTo(window, QPoint(0, 0))
            accent_ignore.append(
                QRect(top_left, b.size()).adjusted(-2, -2, 2, 2)
            )
    hits = light_blocks(shot, ignore=accent_ignore)
    check("VxpMainWindow: không có khối sáng", not hits, f"hits={hits[:6]}")
    bands = light_bands(shot, ignore=accent_ignore)
    check("VxpMainWindow: không có dải sáng mỏng", not bands, f"bands={bands[:4]}")

    # thanh trạng thái phải là nền đậm, không phải một dải accent
    bar = window.findChild(QWidget, "StatusBar")
    if bar is not None:
        bar_px = grab(bar, "statusbar.png")
        img = bar_px.toImage()
        mid = img.pixelColor(bar_px.width() // 2, bar_px.height() // 2)
        check("thanh trạng thái không phải dải accent cam",
              mid.name().lower() not in {"#f59e0b", "#fbbf24"},
              f"màu={mid.name()}")

    # Project Storage: tiêu đề bảng KHÔNG phủ hết bề rộng (các cột cộng lại ~1075px
    # trong khi header rộng ~1400px), nên đây là chỗ dễ lộ vùng nền mặc định
    # (sáng) của QHeaderView nhất — đúng chỗ đã từng lọt một dải trắng.
    # Phải có dự án thật thì _enter_editor mới mở được trang editor.
    import shutil
    tmp = Path(tempfile.mkdtemp(prefix="luas30_theme_proj_"))
    proj = tmp / "ThemeProj"
    shutil.copytree(ROOT / "templates" / "basic", proj)
    window._switch_project(proj)
    app.processEvents()
    window._open_projects_tab()
    app.processEvents()
    hub_shot = grab(window, "project_hub.png")
    shutil.rmtree(tmp, ignore_errors=True)
    hub_hits = light_blocks(hub_shot)
    check("Project Storage: không có khối sáng", not hub_hits, f"hits={hub_hits[:6]}")
    hub_bands = light_bands(hub_shot)
    check("Project Storage: không có dải sáng mỏng", not hub_bands, f"bands={hub_bands[:4]}")

    dialog = MediaTekMREConfigDialog(window, app_name="MRE Snake Retro")
    dialog.resize(560, dialog.sizeHint().height())
    dialog.show()
    dialog.ensurePolished()
    app.processEvents()

    shot = grab(dialog, "mediatek_mre_dialog.png")
    # nút "Lưu thiết lập" CỐ Ý sáng (nền accent cam) — miễn trừ đúng vùng của nó
    ignore = []
    save_btn = dialog.findChild(QPushButton, "MRESaveButton")
    if save_btn is not None:
        top_left = save_btn.mapTo(dialog, QPoint(0, 0))
        ignore.append(QRect(top_left, save_btn.size()).adjusted(-2, -2, 2, 2))
    hits = light_blocks(shot, ignore=ignore)
    check("Hộp thoại MRE: không có khối sáng", not hits, f"hits={hits[:6]}")

    for name, widget in (
        ("trường APPNAME", dialog.app_name),
        ("combo Màn hình", dialog.resolution),
        ("combo Chipset", dialog.chipset),
        ("combo Heap RAM", dialog.ram),
    ):
        g = widget.geometry()
        check(f"{name} nằm trong hộp thoại",
              g.right() <= dialog.width() and g.bottom() <= dialog.height(),
              f"g={g.right()}x{g.bottom()} vs {dialog.width()}x{dialog.height()}")

    for button in dialog.findChildren(QPushButton):
        if button.text():
            check(f"nút '{button.text()}' không bị cắt chữ",
                  button.width() >= button.sizeHint().width(),
                  f"w={button.width()} hint={button.sizeHint().width()}")

    dialog.close()
    window.close()

    check_ai_tab_badges(app, out_dir)
    check_tab_close(app, out_dir)

    if shots:
        print("  saved " + ", ".join(str(p) for p in shots), flush=True)

    QTimer.singleShot(0, app.quit)


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", metavar="THƯ_MỤC",
                        help="xuất PNG để soi bằng mắt")
    parser.add_argument("--static-only", action="store_true",
                        help="chỉ kiểm tra tĩnh, không dựng Qt")
    args = parser.parse_args()

    # config tạm — không đụng %APPDATA% thật của người dùng
    sandbox = Path(tempfile.mkdtemp(prefix="luas30_theme_check_"))
    os.environ["LUAS30_APPDATA"] = str(sandbox / "appdata")
    os.environ["LUAS30_PROJECTS"] = str(sandbox / "projects")
    print(f"config tạm: {sandbox}", flush=True)

    check_palette()
    check_contrast()

    if not args.static_only:
        render(Path(args.shots).resolve() if args.shots else None)

    print("\n== KẾT QUẢ ==", flush=True)
    print("FAIL:", FAILS or "không có", flush=True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
