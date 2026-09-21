from __future__ import annotations

import re
from dataclasses import dataclass

from app.ui import palette
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from app.core.project_session import ProjectSession
from app.ui.icons import apply_icon, glyph, icon_font


@dataclass(frozen=True)
class MediaTekProjectConfig:
    template_id: str
    app_name: str
    app_version: str
    vendor: str
    screen_width: int
    screen_height: int
    resolution_id: str
    resolution_label: str
    chipset_id: str
    chipset_label: str
    ram_kb: int
    ram_label: str
    compat_profile: str
    mre_api: str

    def project_metadata(self) -> dict:
        return {
            "name": self.app_name,
            "template": self.template_id,
            "app_version": self.app_version,
            "vendor": self.vendor,
            "ram_kb": self.ram_kb,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "resolution": self.resolution_id,
            "resolution_label": self.resolution_label,
            "mediatek_chipset": self.chipset_id,
            "mediatek_chipset_label": self.chipset_label,
            "runtime_target": "mre-s30plus",
            "compat_profile": self.compat_profile,
            "mre_api": self.mre_api,
            "single_vxp": True,
            "project_wizard": "mediatek-mre-sdk-v1",
        }

    def sdk_metadata(self) -> dict:
        return {
            "schema": 1,
            "platform": "MediaTek MRE",
            "appname": self.app_name,
            "appver": self.app_version,
            "vendor": self.vendor,
            "resolution": {
                "id": self.resolution_id,
                "label": self.resolution_label,
                "width": self.screen_width,
                "height": self.screen_height,
            },
            "chipset": {
                "id": self.chipset_id,
                "label": self.chipset_label,
            },
            "heap_kb": self.ram_kb,
            "heap_label": self.ram_label,
            "compat_profile": self.compat_profile,
            "mre_api": self.mre_api,
        }


PROJECT_TEMPLATE_OPTIONS = (
    ("basic", "Blank Project", "Khung Lua tối giản để bắt đầu từ đầu"),
    ("doodle-quest", "Doodle Quest", "Game mẫu có UI notebook, HUD, combo, 3 màn"),
    ("ninja-runner", "Ninja Runner", "Game runner/parkour mẫu 240x320"),
    ("catbox-mre", "CatBoxMRE", "Mẫu game nâng cao với nhiều hệ thống"),
)


RESOLUTIONS = (
    ("240x320", "240x320  (QVGA - Chuẩn Nokia)", 240, 320),
    ("320x240", "320x240  (QVGA - Ngang)", 320, 240),
    ("176x220", "176x220  (MRE Compact)", 176, 220),
    ("128x160", "128x160  (Legacy MRE)", 128, 160),
)

CHIPSETS = (
    ("MTK6260", "MTK6260  (Nokia 220, 225)", "nokia225-rm1011", "Audio File ProMng"),
    ("MTK6261", "MTK6261  (Nokia 3310 3G, 216)", "s30plus-native", "Audio File ProMng"),
    ("MTK6250", "MTK6250  (Q-Mobile, K-Touch)", "s30plus-native", "Audio File ProMng"),
    ("MTK6225", "MTK6225  (Legacy MRE 2.0)", "s30plus-native", "File ProMng"),
)

RAM_OPTIONS = (
    (512, "512 KB  (MRE nhẹ / thiết bị cũ)"),
    (768, "768 KB  (Ứng dụng nhỏ)") ,
    (1024, "1024 KB  (1MB - Tiêu chuẩn game MRE)"),
    (1536, "1536 KB  (Ứng dụng lớn)") ,
    (2048, "2048 KB  (2MB - Cần firmware hỗ trợ)"),
)

_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,3}(?:[-+][A-Za-z0-9._-]+)?$")


class _TitleBar(QFrame):
    close_requested = None

    def __init__(self, dialog: "MediaTekMREConfigDialog") -> None:
        super().__init__(dialog)
        self.dialog = dialog
        self.setObjectName("MREDialogTitleBar")
        self._drag_origin: QPoint | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 9, 8, 9)
        row.setSpacing(8)

        icon = QLabel(glyph("settings"))
        icon.setObjectName("MREDialogIcon")
        icon.setFont(icon_font(16, char=glyph("settings")))
        icon.setStyleSheet("color: palette.ACCENT;")
        icon.setFixedSize(32, 32)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)
        title = QLabel("Cấu hình MediaTek MRE SDK")
        title.setObjectName("MREDialogTitle")
        subtitle = QLabel("Thiết lập thông số kỹ thuật cho file đóng gói .vxp")
        subtitle.setObjectName("MREDialogSubtitle")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        row.addLayout(text_col, 1)

        close_button = QToolButton()
        close_button.setObjectName("MREDialogClose")
        close_button.setAutoRaise(True)
        apply_icon(close_button, "close", 13, "palette.TEXT_4")
        close_button.setToolTip("Đóng")
        close_button.clicked.connect(dialog.reject)
        row.addWidget(close_button)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.dialog.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.dialog.move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)


class MediaTekMREConfigDialog(QDialog):
    """Project-creation dialog modeled after the user's MRE SDK reference video."""

    def __init__(
        self,
        parent=None,
        *,
        app_name: str = "",
        app_version: str = "1.0.0",
        vendor: str = "LuaS30",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MediaTekMREConfigDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumWidth(548)
        self.setMaximumWidth(620)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("MREDialogCard")
        outer.addWidget(card)

        root = QVBoxLayout(card)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(_TitleBar(self))

        body = QWidget()
        body.setObjectName("MREDialogBody")
        grid = QGridLayout(body)
        grid.setContentsMargins(22, 18, 22, 18)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self.template = QComboBox()
        self.template.setObjectName("MRECombo")
        for template_id, label, description in PROJECT_TEMPLATE_OPTIONS:
            self.template.addItem(f"{label} — {description}", template_id)
        self.template.setCurrentIndex(1)

        self.app_name = QLineEdit(app_name)
        self.app_name.setObjectName("MREField")
        self.app_name.setPlaceholderText("Ví dụ: MRE Snake Retro")

        self.app_version = QLineEdit(app_version)
        self.app_version.setObjectName("MREField")
        self.app_version.setPlaceholderText("1.0.0")

        self.vendor = QLineEdit(vendor)
        self.vendor.setObjectName("MREField")
        self.vendor.setPlaceholderText("LuaS30")

        self.resolution = QComboBox()
        self.resolution.setObjectName("MRECombo")
        for rid, label, width, height in RESOLUTIONS:
            self.resolution.addItem(label, (rid, width, height))

        self.chipset = QComboBox()
        self.chipset.setObjectName("MRECombo")
        for cid, label, compat, api in CHIPSETS:
            self.chipset.addItem(label, (cid, compat, api))

        self.ram = QComboBox()
        self.ram.setObjectName("MRECombo")
        for value, label in RAM_OPTIONS:
            self.ram.addItem(label, value)
        self.ram.setCurrentIndex(self.ram.findData(1024))

        self.path_preview = QLabel()
        self.path_preview.setObjectName("MREPathPreview")
        self.path_preview.setWordWrap(True)

        self._label(grid, "Mẫu dự án", 0, 0, 1, 2)
        grid.addWidget(self.template, 1, 0, 1, 2)

        self._label(grid, "Tên ứng dụng (APPNAME)", 2, 0)
        self._label(grid, "Phiên bản (APPVER)", 2, 1)
        grid.addWidget(self.app_name, 3, 0)
        grid.addWidget(self.app_version, 3, 1)

        self._label(grid, "Nhà phát triển (VENDOR)", 4, 0, 1, 2)
        grid.addWidget(self.vendor, 5, 0, 1, 2)

        self._label(grid, "Màn hình (Resolution)", 6, 0)
        self._label(grid, "Chipset MediaTek", 6, 1)
        grid.addWidget(self.resolution, 7, 0)
        grid.addWidget(self.chipset, 7, 1)

        self._label(grid, "Dung lượng Heap RAM cấp phát", 8, 0, 1, 2)
        grid.addWidget(self.ram, 9, 0, 1, 2)

        hint = QLabel(
            "AppID được tạo tự động. Chọn Doodle Quest để tạo sẵn game có "
            "Splash/Menu/HUD/gameplay notebook. MTK6260 mặc định dùng profile "
            "Nokia 225 / S30+ native."
        )
        hint.setObjectName("MREDialogHint")
        hint.setWordWrap(True)
        grid.addWidget(hint, 10, 0, 1, 2)

        grid.addWidget(self.path_preview, 11, 0, 1, 2)
        root.addWidget(body)

        footer = QFrame()
        footer.setObjectName("MREDialogFooter")
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(22, 11, 22, 15)
        footer_row.setSpacing(8)
        footer_row.addStretch(1)

        cancel = QPushButton("Hủy bỏ")
        cancel.setObjectName("MRECancelButton")
        cancel.clicked.connect(self.reject)
        footer_row.addWidget(cancel)

        save = QPushButton("Lưu thiết lập")
        save.setObjectName("MRESaveButton")
        apply_icon(save, "save", 13, "palette.BG_SURFACE")
        save.clicked.connect(self._validate_and_accept)
        save.setDefault(True)
        footer_row.addWidget(save)
        root.addWidget(footer)

        self.app_name.textChanged.connect(self._update_preview)
        self.chipset.currentIndexChanged.connect(self._chipset_changed)
        self._update_preview()

    @staticmethod
    def _label(
        grid: QGridLayout,
        text: str,
        row: int,
        column: int,
        row_span: int = 1,
        col_span: int = 1,
    ) -> None:
        label = QLabel(text)
        label.setObjectName("MREFieldLabel")
        grid.addWidget(label, row, column, row_span, col_span)

    def set_project_root_preview(self, base_path: str) -> None:
        self.setProperty("projectRootBase", base_path)
        self._update_preview()

    def _update_preview(self) -> None:
        base = str(self.property("projectRootBase") or "")
        name = self.app_name.text().strip() or "<APPNAME>"
        if base:
            self.path_preview.setText(f"Project: {base}\\{name}")
        else:
            self.path_preview.setText(f"Project folder: {name}")

    def _chipset_changed(self, _index: int) -> None:
        data = self.chipset.currentData()
        if not data:
            return
        cid = data[0]
        recommended = {
            "MTK6260": 1024,
            "MTK6261": 1024,
            "MTK6250": 768,
            "MTK6225": 512,
        }.get(cid, 1024)
        idx = self.ram.findData(recommended)
        if idx >= 0:
            self.ram.setCurrentIndex(idx)

    def _validate_and_accept(self) -> None:
        name = self.app_name.text().strip()
        try:
            ProjectSession.validate_project_name(name)
        except ValueError as exc:
            QMessageBox.warning(self, "APPNAME không hợp lệ", str(exc))
            self.app_name.setFocus()
            return

        version = self.app_version.text().strip()
        if not version or not _VERSION_RE.fullmatch(version):
            QMessageBox.warning(
                self,
                "APPVER không hợp lệ",
                "Phiên bản nên có dạng 1.0.0 hoặc 1.0.0-beta.",
            )
            self.app_version.setFocus()
            return

        if not self.vendor.text().strip():
            QMessageBox.warning(
                self,
                "VENDOR không hợp lệ",
                "Nhà phát triển không được để trống.",
            )
            self.vendor.setFocus()
            return

        self.accept()

    def configuration(self) -> MediaTekProjectConfig:
        rid, width, height = self.resolution.currentData()
        cid, compat, api = self.chipset.currentData()
        ram_kb = int(self.ram.currentData())
        return MediaTekProjectConfig(
            template_id=str(self.template.currentData() or "basic"),
            app_name=ProjectSession.validate_project_name(self.app_name.text()),
            app_version=self.app_version.text().strip(),
            vendor=self.vendor.text().strip(),
            screen_width=int(width),
            screen_height=int(height),
            resolution_id=str(rid),
            resolution_label=self.resolution.currentText(),
            chipset_id=str(cid),
            chipset_label=self.chipset.currentText(),
            ram_kb=ram_kb,
            ram_label=self.ram.currentText(),
            compat_profile=str(compat),
            mre_api=str(api),
        )
