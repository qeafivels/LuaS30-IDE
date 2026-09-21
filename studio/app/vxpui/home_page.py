"""Home/dashboard page for LuaS30 projects, styled after VXPEngine's HomePage."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.services.project_library import ProjectRecord
from app.vxpui.icons import app_icon, icon


def _preview_variant(record: ProjectRecord) -> int:
    digest = hashlib.md5(str(record.root).lower().encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 6


class ProjectPreview(QWidget):
    """Asset-free painted preview so project cards work immediately."""

    def __init__(self, variant: int = 0, parent=None):
        super().__init__(parent)
        self.variant = variant % 6
        self.setFixedHeight(132)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect().adjusted(0, 0, -1, -1))
        clip = QPainterPath()
        clip.addRoundedRect(rect, 9, 9)
        painter.setClipPath(clip)

        palettes = [
            ("#41A6E8", "#18385E", "#4E8C3A", "#814721"),
            ("#26314C", "#101522", "#2D5D47", "#1A352C"),
            ("#7254A5", "#202039", "#784D84", "#3E274E"),
            ("#2B8D7F", "#17354A", "#386D48", "#6F4728"),
            ("#A14D78", "#24152E", "#5E354D", "#311A32"),
            ("#303A67", "#101628", "#34476F", "#1A243E"),
        ]
        sky_top, sky_bottom, grass, dirt = palettes[self.variant]
        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor(sky_top))
        gradient.setColorAt(1, QColor(sky_bottom))
        painter.fillRect(rect, gradient)

        width, height = int(rect.width()), int(rect.height())
        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QColor(255, 255, 255, 24))
        mountain = QPainterPath()
        mountain.moveTo(0, height * 0.70)
        mountain.lineTo(width * 0.18, height * 0.34)
        mountain.lineTo(width * 0.34, height * 0.67)
        mountain.lineTo(width * 0.53, height * 0.26)
        mountain.lineTo(width * 0.72, height * 0.69)
        mountain.lineTo(width, height * 0.40)
        mountain.lineTo(width, height)
        mountain.lineTo(0, height)
        painter.drawPath(mountain)

        painter.setBrush(QColor(dirt))
        painter.drawRect(0, int(height * 0.76), width, int(height * 0.24))
        painter.setBrush(QColor(grass))
        painter.drawRect(0, int(height * 0.73), width, 7)

        for x, y, w in ((0.16, 0.58, 0.22), (0.54, 0.45, 0.20), (0.78, 0.62, 0.17)):
            px, py, pw = int(width * x), int(height * y), int(width * w)
            painter.setBrush(QColor(dirt))
            painter.drawRoundedRect(QRectF(px, py, pw, 18), 3, 3)
            painter.setBrush(QColor(grass))
            painter.drawRect(px, py, pw, 5)

        player_x, player_y = int(width * 0.42), int(height * 0.62)
        painter.setBrush(QColor("#EF665C"))
        painter.drawRoundedRect(QRectF(player_x, player_y, 15, 20), 4, 4)
        painter.setBrush(QColor("#F5C26B"))
        painter.drawEllipse(player_x + 3, player_y - 7, 10, 10)

        painter.setBrush(QColor("#F7C84A"))
        for x in (0.48, 0.58, 0.68):
            painter.drawEllipse(int(width * x), int(height * 0.34), 8, 8)

        painter.setClipping(False)
        painter.setPen(QPen(QColor("#303049"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 9, 9)


class ProjectCard(QFrame):
    open_requested = Signal(object)
    rename_requested = Signal(object)
    remove_requested = Signal(object)

    def __init__(self, project: ProjectRecord, compact: bool = False, parent=None):
        super().__init__(parent)
        self.project = project
        self.setObjectName("ProjectCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(210)
        self.setMaximumWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 10)
        root.setSpacing(8)

        root.addWidget(ProjectPreview(_preview_variant(project)))

        title_row = QHBoxLayout()
        title = QLabel(project.display_name)
        title.setObjectName("ProjectCardTitle")
        title.setToolTip(project.display_name)
        title_row.addWidget(title, 1)

        menu_button = QToolButton()
        menu_button.setObjectName("CardMenuButton")
        menu_button.setIcon(icon("fa5s.ellipsis-v"))
        menu_button.setIconSize(QSize(12, 12))
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(menu_button)
        action_open = menu.addAction(icon("fa5s.external-link-alt"), "Mở trong trình soạn thảo")
        action_open.triggered.connect(lambda: self.open_requested.emit(self.project))
        action_folder = menu.addAction(icon("fa5s.folder-open"), "Hiện vị trí thư mục")
        action_folder.triggered.connect(self._show_folder)
        menu.addSeparator()
        action_rename = menu.addAction(icon("fa5s.pen"), "Đổi tên project")
        action_rename.triggered.connect(lambda: self.rename_requested.emit(self.project))
        action_remove = menu.addAction(icon("fa5s.trash-alt", "#EF747A"), "Xóa project")
        action_remove.triggered.connect(lambda: self.remove_requested.emit(self.project))
        menu_button.setMenu(menu)
        title_row.addWidget(menu_button)
        root.addLayout(title_row)

        timestamp = QLabel(f"Đã sửa {project.modified_text} • {project.size_text}")
        timestamp.setObjectName("ProjectCardMeta")
        root.addWidget(timestamp)

        footer = QHBoxLayout()
        framework_badge = QLabel(project.runtime_target or "mre-s30plus")
        framework_badge.setObjectName("FrameworkBadge")
        framework_badge.setToolTip("Lua → ARM VXP • MRE S30+ • chạy bằng VXPEmu")
        footer.addWidget(framework_badge)

        native_badge = QLabel(f"AppID {project.app_id}")
        native_badge.setObjectName("NativeBadge")
        native_badge.setToolTip("Nhận dạng MRE application trong project.json")
        footer.addWidget(native_badge)

        path_label = QLabel(self._short_path(str(project.root)))
        path_label.setObjectName("ProjectCardPath")
        path_label.setToolTip(str(project.root))
        footer.addWidget(path_label, 1)
        root.addLayout(footer)

    @staticmethod
    def _short_path(value: str) -> str:
        path = Path(value)
        parent = str(path.parent)
        if len(parent) > 28:
            parent = "…" + parent[-27:]
        return parent

    def _show_folder(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.project.root)))

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.project)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class HomePage(QWidget):
    new_project_requested = Signal()
    open_project_folder_requested = Signal()
    project_open_requested = Signal(object)
    project_rename_requested = Signal(object)
    project_remove_requested = Signal(object)
    documentation_requested = Signal()

    def __init__(self, version: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("HomePage")
        self._projects: list[ProjectRecord] = []
        self._mode = "home"  # "home" = 4 dự án gần đây, "projects" = toàn bộ
        self._grid_columns = 4
        self._compact_mode = False
        self._needs_grid_rebuild = True
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(100)
        self._reflow_timer.timeout.connect(self._reflow_projects)

        root = QHBoxLayout(self)
        self.root_layout = root
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = self._build_sidebar(version)
        root.addWidget(self.sidebar)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("HomeScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content.setObjectName("HomeContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(38, 28, 38, 34)
        self.content_layout.setSpacing(18)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Chào mừng trở lại")
        self.home_title = title
        title.setObjectName("HomeTitle")
        subtitle = QLabel(
            "Tạo game MRE Lua 240×320 hoặc 320×240; màn Home chỉ tập trung tạo và mở dự án."
        )
        self.home_subtitle = subtitle
        subtitle.setObjectName("HomeSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        open_button = QPushButton("Mở dự án")
        self.open_button = open_button
        open_button.setObjectName("SecondaryAction")
        open_button.setIcon(icon("fa5s.folder-open"))
        open_button.clicked.connect(self.open_project_folder_requested.emit)
        new_button = QPushButton("Dự án mới")
        self.new_button = new_button
        new_button.setObjectName("PrimaryAction")
        new_button.setIcon(icon("fa5s.plus", "#FFFFFF"))
        new_button.clicked.connect(self.new_project_requested.emit)
        header.addWidget(open_button)
        header.addWidget(new_button)
        self.content_layout.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("HomeDivider")
        self.content_layout.addWidget(divider)

        self.all_section = QWidget()
        all_layout = QVBoxLayout(self.all_section)
        all_layout.setContentsMargins(0, 0, 0, 0)
        all_layout.setSpacing(12)
        all_head = QHBoxLayout()
        all_title = QLabel("Tất cả dự án")
        all_title.setObjectName("SectionTitle")
        self.section_title = all_title
        all_head.addWidget(all_title)
        all_head.addStretch()
        self.section_action = QPushButton("Xem tất cả →")
        self.section_action.setObjectName("SectionAction")
        self.section_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.section_action.clicked.connect(self._show_all_projects)
        self.section_action.hide()
        all_head.addWidget(self.section_action)
        self.count_label = QLabel("0 dự án")
        self.count_label.setObjectName("SectionCount")
        all_head.addWidget(self.count_label)
        all_layout.addLayout(all_head)
        self.all_grid = QGridLayout()
        self.all_grid.setHorizontalSpacing(12)
        self.all_grid.setVerticalSpacing(14)
        self.all_grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        all_layout.addLayout(self.all_grid)
        self.content_layout.addWidget(self.all_section)
        self.content_layout.addStretch()

        self.empty_state = self._build_empty_state()
        self.content_layout.insertWidget(2, self.empty_state)
        self.empty_state.hide()

        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

    def _build_sidebar(self, version: str) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("HomeSidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        self.sidebar_layout = layout
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(6)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.sidebar_buttons: list[tuple[QPushButton, str]] = []

        def nav(text: str, icon_name: str, mode: str, checked: bool = False) -> QPushButton:
            button = QPushButton(text)
            button.setObjectName("SidebarButton")
            button.setCheckable(True)
            button.setChecked(checked)
            button.setIcon(icon(icon_name))
            button.setIconSize(QSize(18, 18))
            button.clicked.connect(lambda: self._set_filter(mode))
            self.nav_group.addButton(button)
            self.sidebar_buttons.append((button, text))
            button.setToolTip(text)
            layout.addWidget(button)
            return button

        nav("Trang chủ", "fa5s.home", "home", True)
        self.projects_nav = nav("Dự án", "fa5s.folder", "projects")

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("SidebarDivider")
        layout.addWidget(divider)

        section = QLabel("CÔNG CỤ")
        section.setObjectName("SidebarSection")
        layout.addWidget(section)

        docs = QPushButton("Tài liệu")
        self.docs_button = docs
        docs.setObjectName("SidebarUtility")
        docs.setIcon(icon("fa5s.book-open"))
        docs.clicked.connect(self.documentation_requested.emit)
        layout.addWidget(docs)

        layout.addStretch()

        engine = QFrame()
        engine.setObjectName("EngineCard")
        engine_layout = QHBoxLayout(engine)
        engine_layout.setContentsMargins(12, 10, 12, 10)
        engine_icon = QLabel()
        engine_icon.setPixmap(app_icon().pixmap(28, 28))
        engine_layout.addWidget(engine_icon)
        text_box = QVBoxLayout()
        name = QLabel("LuaS30 IDE")
        self.engine_name_label = name
        name.setObjectName("EngineCardTitle")
        version_text = QLabel(f"Phiên bản {version}" if version else "Lua → VXP core")
        self.engine_version_label = version_text
        version_text.setObjectName("EngineCardMeta")
        text_box.addWidget(name)
        text_box.addWidget(version_text)
        engine_layout.addLayout(text_box, 1)
        layout.addWidget(engine)
        return sidebar

    def _build_empty_state(self) -> QWidget:
        state = QFrame()
        state.setObjectName("EmptyState")
        layout = QVBoxLayout(state)
        layout.setContentsMargins(24, 34, 24, 34)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image = QLabel()
        image.setPixmap(icon("fa5s.folder-plus", "#FF8A00").pixmap(42, 42))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Chưa có dự án nào")
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc = QLabel("Tạo dự án Lua → VXP gọn nhẹ; build ARM cho máy thật và chạy bằng VXPEmu.")
        desc.setObjectName("EmptyDescription")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button = QPushButton("Tạo dự án mới")
        button.setObjectName("PrimaryAction")
        button.setIcon(icon("fa5s.plus", "#FFFFFF"))
        button.clicked.connect(self.new_project_requested.emit)
        layout.addWidget(image)
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(6)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignCenter)
        return state

    def set_projects(self, projects: list[ProjectRecord]) -> None:
        self._projects = list(projects)
        self._needs_grid_rebuild = True
        self._clear_grid(self.all_grid)
        self.count_label.setText(f"{len(projects)} dự án")
        self.empty_state.setVisible(not projects)
        self.all_section.setVisible(bool(projects))
        self._update_section_head()
        self._reflow_projects()

    def set_compact_mode(self, enabled: bool) -> None:
        if self._compact_mode == enabled:
            return
        self._compact_mode = enabled
        self._needs_grid_rebuild = True
        self.sidebar.setFixedWidth(72 if enabled else 248)
        self.sidebar_layout.setContentsMargins(
            10 if enabled else 16, 14 if enabled else 18,
            10 if enabled else 16, 14 if enabled else 18,
        )
        for button, label in self.sidebar_buttons:
            button.setText("" if enabled else label)
        self.docs_button.setText("" if enabled else "Tài liệu")
        self.docs_button.setToolTip("Tài liệu")
        self.engine_name_label.setVisible(not enabled)
        self.engine_version_label.setVisible(not enabled)
        self.content_layout.setContentsMargins(
            18 if enabled else 38, 20 if enabled else 28,
            18 if enabled else 38, 28,
        )
        self.home_subtitle.setVisible(not enabled)
        self.open_button.setText("" if enabled else "Mở dự án")
        self.open_button.setToolTip("Mở dự án")
        self.new_button.setText("" if enabled else "Dự án mới")
        self.new_button.setToolTip("Dự án mới")
        self._schedule_reflow()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_reflow()

    def _schedule_reflow(self) -> None:
        if not self._reflow_timer.isActive():
            self._reflow_timer.start()

    def _visible_projects(self) -> list[ProjectRecord]:
        # scan() đã sắp xếp theo modified giảm dần nên 4 mục đầu là mới nhất.
        return self._projects[:4] if self._mode == "home" else self._projects

    def _update_section_head(self) -> None:
        recent = self._mode == "home" and len(self._projects) > 4
        self.section_title.setText(
            "Dự án gần đây" if self._mode == "home" else "Tất cả dự án"
        )
        self.section_action.setVisible(recent)

    def _show_all_projects(self) -> None:
        self.projects_nav.setChecked(True)
        self._set_filter("projects")

    def _reflow_projects(self) -> None:
        available = max(220, self.scroll.viewport().width() - (36 if self._compact_mode else 76))
        columns = max(1, min(4, available // 250))
        visible = self._visible_projects()
        if (
            not self._needs_grid_rebuild
            and columns == self._grid_columns
            and self.all_grid.count() == len(visible)
        ):
            return
        self._grid_columns = columns
        self._needs_grid_rebuild = False
        self._clear_grid(self.all_grid)
        for index, project in enumerate(visible):
            self.all_grid.addWidget(self._make_card(project), index // columns, index % columns)
        for column in range(columns):
            self.all_grid.setColumnStretch(column, 1)

    def _make_card(self, project: ProjectRecord) -> ProjectCard:
        card = ProjectCard(project)
        card.open_requested.connect(self.project_open_requested.emit)
        card.rename_requested.connect(self.project_rename_requested.emit)
        card.remove_requested.connect(self.project_remove_requested.emit)
        return card

    @staticmethod
    def _clear_grid(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _set_filter(self, mode: str) -> None:
        self._mode = mode
        self.all_section.setVisible(mode in {"home", "projects"} and bool(self._projects))
        self.empty_state.setVisible(not self._projects)
        self._needs_grid_rebuild = True
        self._update_section_head()
        self._reflow_projects()
        self.scroll.verticalScrollBar().setValue(0)
