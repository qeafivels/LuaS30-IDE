"""LuaS30 IDE — VXPEngine-style frameless shell driving the Lua → VXP core.

The chrome (frameless window, custom title bar with embedded menu, Home page
with project cards, toolbar + three-column workspace + bottom console and
status bar) mirrors D:\\MRE\\VXPEngine's UI 1:1.  Everything below the chrome
is the original LuaS30 pipeline: BuildService / EmulatorService drive
tools/build.py and tools/run_emulator.py through the LuaRunner adapter.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QDateTime, QEvent, QPoint, QSize, Qt, QUrl, QTimer
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QColor, QIcon, QPalette
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMenuBar,
    QMessageBox, QPushButton, QSplitter, QStackedWidget, QTabWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from app.core.project_session import ProjectSession
from app.core.workspace_session import WorkspaceSessionStore
from app.core.paths import resolve_script, tool_python
from app.core.utf8 import decode_process_bytes, utf8_qprocess_environment
from app.editor.editor_group_manager import EditorGroupManager
from app.editor.explorer_panel import ExplorerPanel
from app.editor.find_replace import FindReplaceBar
from app.editor.project_index import ProjectIndex
from app.editor.project_search import ProjectSearchPanel
from app.services.ai_change_service import AIChangeService, PreparedChangeSet
from app.services.build_service import BuildService
from app.services.compat_matrix_service import CompatMatrixService
from app.services.emulator_service import EmulatorService
from app.services.extension_service import ExtensionService
from app.services.project_library import ProjectLibraryService, ProjectRecord
from app.ui.about_dialog import AboutDialog
from app.ui.mediatek_mre_dialog import MediaTekMREConfigDialog
from app.vxpui.assets_studio_window import AssetsStudioWindow
from app.vxpui.custom_dialog import (
    ConfirmDialog,
    CustomDialog,
    NoticeDialog,
    RunSessionDialog,
    TextInputDialog,
)
from app.vxpui.home_page import HomePage
from app.vxpui.icons import app_icon, icon
from app.vxpui.lua_runner import LuaRunner
from app.vxpui.panel_frame import PanelFrame
from app.vxpui.task_progress import BottomTaskProgress
from app.vxpui.title_bar import CustomTitleBar
from app.vxpui.toast import AppToast
from app.vxpui.vxpemu_panel import VxpEmuPanel
from app.vxpui.window_state_controller import WindowStateController
from app.views.ai_chat_view import AIChatView
from app.views.ai_diff_view import AIDiffView
from app.views.compat_matrix_view import CompatMatrixView
from app.views.emulator_view import EmulatorView
from app.views.project_doctor_view import ProjectDoctorView
from app.views.project_manager_view import ProjectManagerView
from app.views.settings_view import SettingsView
from app.views.toolchain_doctor_view import ToolchainDoctorView
from app.views.ui_designer_view import UIDesignerView
from app.widgets.bottom_panel import BottomPanel
from app.widgets.vxp_emu_window import VxpEmuWindow

RESIZE_MARGIN = 6

BUILD_TARGETS = (
    ("Build VXP (.vxp)", "fa5s.box", "build"),
    ("Run VXPEmu (build + autostart)", "fa5s.play", "run_vxpemu"),
    ("Clean build folder", "fa5s.broom", "clean"),
)

# Tool tabs that survive a restart via the workspace session file.
_PERSISTENT_TOOL_TABS = ("settings", "projects", "project-doctor", "compat-matrix", "toolchain-doctor", "extensions-market")


class VxpMainWindow(QWidget):
    # Keep in lockstep with the repo-root VERSION file (version-sync guards).
    VERSION = "1.0.1"
    LEFT_COLUMN_MIN_WIDTH = 190

    def __init__(self, engine_root: Path, version: str = "") -> None:
        super().__init__()
        self.engine_root = Path(engine_root).resolve()
        self.version_text = str(version or "").strip() or self.VERSION
        self.setObjectName("VxpMainWindow")
        self.setWindowFlags(Qt.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowIcon(app_icon(str(self.engine_root / "app-icon" / "icon.png")))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1536, 960)
        self.setMinimumSize(760, 520)
        self.setMouseTracking(True)
        self._closing = False

        # ------------------------------------------------ Lua core services
        self.session = ProjectSession(self.engine_root, self)
        self.workspace_session = WorkspaceSessionStore()
        self.project_library = ProjectLibraryService(
            self.session.default_projects_root,
            self.engine_root / "templates" / "basic",
        )
        self.build_service = BuildService(self.engine_root, self)
        self.emulator_service = EmulatorService(self.engine_root, self)
        self.compat_matrix_service = CompatMatrixService(self.engine_root, self)
        self.extension_service = ExtensionService(self.engine_root)
        self.runner = LuaRunner(self.build_service, self.emulator_service, self)
        self.ai_change_service = AIChangeService()
        self._ai_change_set: PreparedChangeSet | None = None
        self._ai_last_applied: PreparedChangeSet | None = None
        self._ai_last_applied_backup: Path | None = None
        self.index = ProjectIndex()

        self._startup_mode = "welcome"
        self._compiler_profile = "auto"
        self._toolchain_root = self.engine_root / "toolchain" / "arm-gcc"
        self._compat_profile = "auto"
        self._mre_sdk_root: Path | None = None
        self.last_manifest: dict = {}
        self._project_meta: dict = {}
        self._console_backlog: list[str] = []
        self._console_visible = False
        self._console_last_height = 190
        self._ai_visible = False
        self._vxp_emu_window: VxpEmuWindow | None = None
        self.run_session_dialog: RunSessionDialog | None = None
        # Chạy thử do Chat AI/`/run` yêu cầu: build + launch VXPEmu screen-only,
        # chờ khung hình ổn định rồi chụp ảnh khói và báo kết quả về AIChatView.
        self._ai_run_active = False
        self._ai_run_reason = ""
        self._ai_run_started = False
        self._ai_run_reported = False
        self._ai_run_attempts = 0
        # Thẻ lỗi trong Chat AI cập nhật realtime theo diagnostic của editor: nén
        # các lần đổi liên tục (gõ phím) về một nhịp 400ms.
        self._ai_problem_timer = QTimer(self)
        self._ai_problem_timer.setSingleShot(True)
        self._ai_problem_timer.setInterval(400)
        self._ai_problem_timer.timeout.connect(self._refresh_ai_problem_card)
        # Nén bão output build/emu: gom nhiều chunk rồi vẽ MỘT lần mỗi nhịp
        # ~60ms, thay vì repaint cả console + build_log + dialog cho TỪNG chunk
        # (nguyên nhân chính gây lag khi compile in hàng trăm dòng).
        self._console_pending: list[str] = []
        self._console_flush_timer = QTimer(self)
        self._console_flush_timer.setSingleShot(True)
        self._console_flush_timer.setInterval(60)
        self._console_flush_timer.timeout.connect(self._flush_console)
        self._env_update_proc = None
        self._resizing = False
        self._resize_edge: str | None = None
        self._drag_start_geo = None
        self._drag_start_pos = None
        self._workspace_save_timer = QTimer(self)
        self._workspace_save_timer.setSingleShot(True)
        self._workspace_save_timer.setInterval(450)
        self._workspace_save_timer.timeout.connect(self._save_workspace_session)
        self._restoring_workspace = False

        # ---------------------------------------------------- frameless shell
        outer = QVBoxLayout(self)
        self.outer_layout = outer
        outer.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        self.root_frame = QFrame()
        self.root_frame.setObjectName("RootFrame")
        self.root_frame.setMouseTracking(True)
        outer.addWidget(self.root_frame)

        self.app_toast = AppToast(self.root_frame)

        root_layout = QVBoxLayout(self.root_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self, title="LuaS30 IDE")
        self.window_state_controller = WindowStateController(
            window=self,
            title_bar=self.title_bar,
            outer_layout=self.outer_layout,
            root_frame=self.root_frame,
            normal_margin=RESIZE_MARGIN,
            parent=self,
        )
        self.title_bar.minimizeRequested.connect(self.window_state_controller.minimize)
        self.title_bar.maximizeRestoreRequested.connect(self.window_state_controller.toggle_maximize_restore)
        self.title_bar.closeRequested.connect(self.close)
        self.title_bar.homeRequested.connect(self._show_home)
        self.title_bar.btn_info.clicked.connect(lambda: self.show_about("about"))
        root_layout.addWidget(self.title_bar)

        self.menu_bar = self._build_menu_bar()
        self.title_bar.set_menu_bar(self.menu_bar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")
        root_layout.addWidget(self.stack, 1)

        self.home_page = HomePage(self.version_text)
        self.home_page.new_project_requested.connect(self.create_project_from_template)
        self.home_page.open_project_folder_requested.connect(self.open_project_dialog)
        self.home_page.project_open_requested.connect(self._open_record_from_home)
        self.home_page.project_rename_requested.connect(self._rename_from_home)
        self.home_page.project_remove_requested.connect(self._remove_from_home)
        self.home_page.documentation_requested.connect(self._open_docs)
        self.stack.addWidget(self.home_page)

        self.editor_page = self._build_editor_page()
        self.stack.addWidget(self.editor_page)

        # Cột TÀI NGUYÊN + UI Designer sống trong cửa sổ riêng kiểu Photoshop
        # (menu Công cụ → "Tài nguyên · UI Designer"); main window chỉ giữ
        # tham chiếu để set_project / refresh / autosave khi thoát.
        self.assets_studio = AssetsStudioWindow(self, self.engine_root)
        self.assets = self.assets_studio.assets
        self.assets_studio.designer.logMessage.connect(self._designer_log)
        self.assets_studio.designer.assetsImported.connect(self._refresh_project_assets)

        # ------------------------------------------------------ runner wiring
        self.runner.output.connect(self._append_console)
        self.runner.started.connect(self._on_runner_started)
        self.runner.running_changed.connect(self._runner_state_changed)
        self.runner.project_structure_changed.connect(self._project_structure_changed)
        self.runner.phase_changed.connect(self._on_phase_changed)
        self.runner.finished.connect(self._on_runner_finished)
        self.runner.environment_checked.connect(self._on_environment_checked)
        self.runner.vxpemu_output.connect(self._on_vxpemu_output)
        self.runner.vxpemu_started.connect(self._on_vxpemu_started)
        self.runner.vxpemu_stopped.connect(self._on_vxpemu_stopped)

        self.emulator_service.state_changed.connect(self._on_emulator_state_label)
        self.emulator_service.launched.connect(self._on_emulator_launched)

        self.compat_matrix_service.started.connect(lambda: self.show_status("Runtime compatibility matrix started"))
        self.compat_matrix_service.output.connect(self._compat_output)
        self.compat_matrix_service.finished.connect(self._compat_finished)

        self._load_initial_state()
        self._show_home()
        QTimer.singleShot(800, self._maybe_first_run_setup)

    # ================================================================ menus
    def _build_menu_bar(self) -> QMenuBar:
        menu_bar = QMenuBar()
        menu_bar.setNativeMenuBar(False)
        menu_bar.setObjectName("MainMenuBar")

        def act(title: str, icon_name: str = "", shortcut: str = "") -> QAction:
            action = QAction(icon(icon_name) if icon_name else QIcon(), title, self)
            if shortcut:
                action.setShortcut(shortcut)
            return action

        file_menu = menu_bar.addMenu("Tệp")
        home_action = act("Home", "fa5s.home", "Ctrl+Shift+H")
        home_action.triggered.connect(self._show_home)
        file_menu.addAction(home_action)
        new_action = act("Dự án Lua mới…", "fa5s.plus", "Ctrl+N")
        new_action.triggered.connect(self.create_project_from_template)
        file_menu.addAction(new_action)
        open_action = act("Mở dự án…", "fa5s.folder-open", "Ctrl+O")
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)
        close_action = act("Đóng dự án", "fa5s.times")
        close_action.triggered.connect(self._close_project)
        file_menu.addAction(close_action)
        file_menu.addSeparator()
        save_action = act("Lưu tất cả", "fa5s.save", "Ctrl+S")
        save_action.triggered.connect(lambda: self.tabs.save_all())
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = act("Thoát", "fa5s.sign-out-alt")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu_bar.addMenu("Chỉnh sửa")
        for label, shortcut, method in (
            ("Hoàn tác", "Ctrl+Z", "undo"),
            ("Làm lại", "Ctrl+Y", "redo"),
            (None, None, None),
            ("Cắt", "Ctrl+X", "cut"),
            ("Sao chép", "Ctrl+C", "copy"),
            ("Dán", "Ctrl+V", "paste"),
            ("Chọn tất cả", "Ctrl+A", "selectAll"),
        ):
            if label is None:
                edit_menu.addSeparator()
                continue
            action = act(label, "", shortcut)
            action.triggered.connect(
                lambda _checked=False, name=method: self._dispatch_focused_editor_method(name)
            )
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        find_action = act("Tìm", "fa5s.search", "Ctrl+F")
        find_action.triggered.connect(lambda: self._show_find(False))
        edit_menu.addAction(find_action)
        replace_action = act("Tìm thay", "fa5s.exchange-alt", "Ctrl+H")
        replace_action.triggered.connect(lambda: self._show_find(True))
        edit_menu.addAction(replace_action)
        definition_action = act("Go to Definition", "fa5s.forward", "F12")
        definition_action.triggered.connect(lambda: self.tabs.current_editor() and self.tabs.current_editor().go_to_definition())
        edit_menu.addAction(definition_action)

        view_menu = menu_bar.addMenu("Xem")
        self.console_toggle_action = act("Bảng dưới (Console / Problems / Terminal)", "fa5s.terminal", "Ctrl+J")
        self.console_toggle_action.setCheckable(True)
        self.console_toggle_action.triggered.connect(self._set_console_visible)
        view_menu.addAction(self.console_toggle_action)
        ai_toggle = act("Chat AI", "fa5s.robot", "Ctrl+Alt+I")
        ai_toggle.setCheckable(True)
        ai_toggle.toggled.connect(self._set_ai_visible)
        self.ai_toggle_action = ai_toggle
        view_menu.addAction(ai_toggle)
        terminal_action = act("Terminal", "fa5s.desktop", "Ctrl+`")
        terminal_action.triggered.connect(self._show_terminal_panel)
        view_menu.addAction(terminal_action)
        view_menu.addSeparator()
        storage_action = act("Project Storage", "fa5s.folder", "Ctrl+Alt+P")
        storage_action.triggered.connect(self._open_projects_tab)
        view_menu.addAction(storage_action)

        project_menu = menu_bar.addMenu("Dự án")
        env_check_action = act("Kiểm tra môi trường / thư viện…", "fa5s.check-circle")
        env_check_action.triggered.connect(self._check_environment)
        project_menu.addAction(env_check_action)
        open_folder = act("Mở thư mục dự án", "fa5s.folder-open")
        open_folder.triggered.connect(self._open_current_project_folder)
        project_menu.addAction(open_folder)
        build_folder = act("Mở thư mục build", "fa5s.folder-open")
        build_folder.triggered.connect(self._open_build_folder)
        project_menu.addAction(build_folder)
        project_menu.addSeparator()
        doctor_action = act("Project Doctor", "fa5s.stethoscope")
        doctor_action.triggered.connect(self._open_project_doctor)
        project_menu.addAction(doctor_action)
        designer_action = act("UI Designer", "fa5s.paint-brush")
        designer_action.triggered.connect(self._open_designer)
        project_menu.addAction(designer_action)

        run_menu = menu_bar.addMenu("Chạy")
        run_vxpemu = act("Run VXPEmu (build ARM + autostart)", "fa5s.play", "F6")
        run_vxpemu.triggered.connect(lambda _checked=False: self._run_build_command("run_vxpemu"))
        run_menu.addAction(run_vxpemu)
        build_arm = act("Build VXP (.vxp cho máy thật)", "fa5s.microchip", "Ctrl+Shift+B")
        build_arm.triggered.connect(lambda _checked=False: self._run_build_command("build"))
        run_menu.addAction(build_arm)
        clean_action = act("Clean Project", "fa5s.broom")
        clean_action.triggered.connect(lambda _checked=False: self._run_build_command("clean"))
        run_menu.addAction(clean_action)
        run_menu.addSeparator()
        stop_action = act("Dừng build", "fa5s.stop", "Shift+F5")
        stop_action.triggered.connect(self.runner.stop)
        run_menu.addAction(stop_action)
        stop_emu = act("Dừng giả lập VXPEmu", "fa5s.power-off")
        stop_emu.triggered.connect(self.runner.stop_vxpemu)
        run_menu.addAction(stop_emu)

        tools_menu = menu_bar.addMenu("Công cụ")
        device_action = act("Thiết bị · VXPEmu", "fa5s.gamepad", "Ctrl+Alt+D")
        device_action.triggered.connect(
            lambda _checked=False: self._open_device_dialog()
        )
        tools_menu.addAction(device_action)
        assets_studio_action = act("Tài nguyên · UI Designer", "fa5s.paint-brush", "Ctrl+Alt+U")
        assets_studio_action.triggered.connect(
            lambda _checked=False: self._open_designer()
        )
        tools_menu.addAction(assets_studio_action)
        tools_menu.addSeparator()
        compat_action = act("Runtime Compatibility Matrix", "fa5s.th")
        compat_action.triggered.connect(self._open_compat_matrix)
        tools_menu.addAction(compat_action)
        toolchain_action = act("Toolchain Doctor", "fa5s.wrench")
        toolchain_action.triggered.connect(self._open_toolchain_doctor)
        tools_menu.addAction(toolchain_action)
        extensions_menu = QMenu("Tiện ích mở rộng", tools_menu)
        extensions_menu.setIcon(icon("fa5s.puzzle-piece"))
        extensions_menu.aboutToShow.connect(
            lambda _checked=False: self._populate_extensions_menu(extensions_menu)
        )
        tools_menu.addMenu(extensions_menu)
        settings_action = act("Cài đặt", "fa5s.cog")
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)
        tools_menu.addSeparator()
        refresh_assets = act("Làm mới tài nguyên / cây dự án", "fa5s.sync-alt", "F5")
        refresh_assets.triggered.connect(self._refresh_project_assets)
        tools_menu.addAction(refresh_assets)
        clear_console = act("Xóa bảng điều khiển", "fa5s.eraser")
        clear_console.triggered.connect(lambda: self.bottom.console.clear())
        tools_menu.addAction(clear_console)

        help_menu = menu_bar.addMenu("Trợ giúp")
        docs_action = act("Tài liệu LuaS30", "fa5s.book-open", "F1")
        docs_action.triggered.connect(self._open_docs)
        help_menu.addAction(docs_action)
        update_action = act("Kiểm tra & cập nhật môi trường…", "fa5s.download", "Ctrl+U")
        update_action.triggered.connect(self._update_environment)
        help_menu.addAction(update_action)
        first_run_setup_action = act("Chạy lại thiết lập lần đầu…", "fa5s.magic")
        first_run_setup_action.triggered.connect(lambda: self._run_first_run_setup(force=True))
        help_menu.addAction(first_run_setup_action)
        help_menu.addSeparator()
        about_action = act("Giới thiệu LuaS30 IDE", "fa5s.info-circle")
        about_action.triggered.connect(lambda: self.show_about("about"))
        help_menu.addAction(about_action)
        credits_action = act("Credits and Third-party Libraries", "fa5s.users")
        credits_action.triggered.connect(lambda: self.show_about("credits"))
        help_menu.addAction(credits_action)

        self._apply_menu_contrast(menu_bar)
        return menu_bar

    @staticmethod
    def _apply_menu_contrast(menu_bar: QMenuBar) -> None:
        """Keep title/menu text readable even when Windows uses a light palette."""
        palette = menu_bar.palette()
        for role, color in (
            (QPalette.ColorRole.Window, "#111122"),
            (QPalette.ColorRole.Base, "#19192E"),
            (QPalette.ColorRole.Button, "#19192E"),
            (QPalette.ColorRole.WindowText, "#D8DBE7"),
            (QPalette.ColorRole.Text, "#D8DBE7"),
            (QPalette.ColorRole.ButtonText, "#D8DBE7"),
            (QPalette.ColorRole.Highlight, "#1C2A3B"),
            (QPalette.ColorRole.HighlightedText, "#FFFFFF"),
        ):
            palette.setColor(role, QColor(color))
        menu_bar.setPalette(palette)
        for menu in menu_bar.findChildren(QMenu):
            menu.setPalette(palette)

    # ========================================================= editor page
    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("EditorPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_tool_bar())
        body = QWidget()
        body.setObjectName("EditorBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._build_activity_bar())
        body_layout.addWidget(self._build_content_area(), 1)
        layout.addWidget(body, 1)
        layout.addWidget(self._build_status_bar())
        return page

    def _build_activity_bar(self) -> QWidget:
        """Thanh icon dọc trái kiểu VS Code: Explorer · Search · Console · AI · Settings."""
        rail = QFrame()
        rail.setObjectName("ActivityBar")
        rail.setFixedWidth(46)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(4)
        self._activity_buttons: dict[str, QToolButton] = {}

        def button(key: str, fa_name: str, tooltip: str, handler):
            item = QToolButton()
            item.setObjectName("ActivityButton")
            item.setIcon(icon(fa_name))
            item.setIconSize(QSize(17, 17))
            item.setFixedSize(34, 34)
            item.setCheckable(True)
            item.setToolTip(tooltip)
            item.clicked.connect(lambda _checked=False: handler())
            self._activity_buttons[key] = item
            layout.addWidget(item, 0, Qt.AlignmentFlag.AlignHCenter)
            return item

        button("explorer", "fa5s.folder", "Explorer — cây dự án (Ctrl+B)", self._activity_explorer)
        button("search", "fa5s.search", "Tìm kiếm trong dự án", self._activity_search)
        button("console", "fa5s.terminal", "Console, Problems, Terminal, HEX (Ctrl+J)",
               self._toggle_console_panel)
        button("ai", "fa5s.robot", "Chat AI (Ctrl+Alt+I)",
               lambda: self._set_ai_visible(not self._ai_visible))
        # Icon extension đã cài — như VS Code, mỗi tiện ích một nút ở cột trái.
        self._activity_ext_box = QVBoxLayout()
        self._activity_ext_box.setSpacing(4)
        layout.addLayout(self._activity_ext_box)
        layout.addStretch(1)
        button("settings", "fa5s.cog", "Cài đặt Studio", self._open_settings)
        self._refresh_activity_extensions()
        return rail

    def _refresh_activity_extensions(self) -> None:
        """Nạp lại icon extension trên activity bar theo danh sách đã cài."""
        box = getattr(self, "_activity_ext_box", None)
        if box is None:
            return
        while box.count():
            item = box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._activity_ext_buttons: dict[str, QToolButton] = {}
        for manifest in self.extension_service.discover():
            if not self.extension_service.is_installed(manifest.id):
                continue
            item = QToolButton()
            item.setObjectName("ActivityButton")
            item.setIcon(icon(manifest.icon))
            item.setIconSize(QSize(17, 17))
            item.setFixedSize(34, 34)
            item.setToolTip(f"{manifest.name} — tiện ích mở rộng")
            item.clicked.connect(
                lambda _checked=False, ext_id=manifest.id: self._open_extension(ext_id)
            )
            box.addWidget(item, 0, Qt.AlignmentFlag.AlignHCenter)
            self._activity_ext_buttons[manifest.id] = item

    def _activity_explorer(self) -> None:
        self._activity_show_pane(0)

    def _activity_search(self) -> None:
        self._activity_show_pane(1)

    def _activity_show_pane(self, tab_index: int) -> None:
        """Nhét icon Explorer/Search: đang mở đúng ngăn thì đóng, ngược lại mở+chọn ngăn."""
        # isHidden() chứ không isVisible(): trước khi window hiện, isVisible()
        # của mọi child đều False dù panel không bị ẩn.
        if not self.project_panel_frame.isHidden():
            if self.left_tabs.currentIndex() == tab_index:
                self._toggle_left_column()
                return
            self.left_tabs.setCurrentIndex(tab_index)
        else:
            self.project_panel_frame.setVisible(True)
            self.explorer_toggle_button.setChecked(True)
            self.left_tabs.setCurrentIndex(tab_index)
        self._update_activity_bar()
        self._schedule_workspace_save()

    def _update_activity_bar(self) -> None:
        buttons = getattr(self, "_activity_buttons", None)
        if not buttons:
            return
        left_visible = not self.project_panel_frame.isHidden()
        left_index = self.left_tabs.currentIndex()
        buttons["explorer"].setChecked(left_visible and left_index == 0)
        buttons["search"].setChecked(left_visible and left_index == 1)
        buttons["console"].setChecked(self._console_visible)
        buttons["ai"].setChecked(self._ai_visible)

    def _build_tool_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("MainToolBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 3, 10, 3)
        layout.setSpacing(2)

        home = QToolButton()
        home.setObjectName("ToolbarHome")
        home.setIcon(icon("fa5s.home"))
        home.setIconSize(QSize(14, 14))
        home.setFixedSize(29, 29)
        home.setToolTip("Về màn hình Home")
        home.clicked.connect(self._show_home)
        layout.addWidget(home)
        layout.addWidget(self._toolbar_separator())

        self.run_button = self._command_button(
            "RunBtn", "Run", "fa5s.play", "Lưu mã, build ARM .vxp và mở VXPEmu (F6)",
            lambda: self._run_build_command("run_vxpemu"),
        )
        layout.addWidget(self.run_button)
        self.stop_button = self._command_button(
            "StopBtn", "Stop", "fa5s.stop", "Dừng build / giải mã pipeline", self.runner.stop
        )
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        self.check_button = self._command_button(
            "CheckBtn", "Check", "fa5s.check-circle",
            "Kiểm tra Python, ARM GCC, MRE SDK và VXPEmu", self._check_environment,
        )
        layout.addWidget(self.check_button)

        layout.addWidget(self._toolbar_separator())
        self.build_button = QToolButton()
        self.build_button.setObjectName("BuildBtn")
        self.build_button.setText("Build")
        self.build_button.setProperty("responsiveText", "Build")
        self.build_button.setIcon(icon("fa5s.box"))
        self.build_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.build_button.setIconSize(QSize(14, 14))
        self.build_button.setFixedHeight(29)
        self.build_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        build_menu = QMenu(self.build_button)
        self._build_menu_actions: list[QAction] = []
        for index, (label, icon_name, command) in enumerate(BUILD_TARGETS):
            action = QAction(icon(icon_name), label, build_menu)
            action.setCheckable(True)
            action.setChecked(index == 0)
            action.triggered.connect(
                lambda _checked=False, target=index: self._select_and_run_target(target)
            )
            build_menu.addAction(action)
            self._build_menu_actions.append(action)
        self.build_button.setMenu(build_menu)
        self.build_button.clicked.connect(lambda: self._run_build_command(BUILD_TARGETS[0][2]))
        self._selected_build_target_index = 0
        self._update_build_button_label()
        layout.addWidget(self.build_button)

        layout.addWidget(self._toolbar_separator())
        self.designer_button = self._command_button(
            "DesignerBtn", "Designer", "fa5s.paint-brush",
            "Mở cửa sổ Tài nguyên · UI Designer", self._open_designer
        )
        self.designer_button.setMinimumWidth(0)
        layout.addWidget(self.designer_button)

        layout.addStretch()

        self.explorer_toggle_button = QToolButton()
        self.explorer_toggle_button.setObjectName("PanelToggleBtn")
        self.explorer_toggle_button.setIcon(icon("fa5s.folder"))
        self.explorer_toggle_button.setIconSize(QSize(14, 14))
        self.explorer_toggle_button.setFixedSize(29, 29)
        self.explorer_toggle_button.setCheckable(True)
        self.explorer_toggle_button.setChecked(True)
        self.explorer_toggle_button.setToolTip("Ẩn/hiện Explorer (Ctrl+B)")
        self.explorer_toggle_button.clicked.connect(self._toggle_left_column)
        layout.addWidget(self.explorer_toggle_button)

        self.ai_button = QToolButton()
        self.ai_button.setObjectName("PanelToggleBtn")
        self.ai_button.setIcon(icon("fa5s.robot"))
        self.ai_button.setIconSize(QSize(14, 14))
        self.ai_button.setFixedSize(29, 29)
        self.ai_button.setCheckable(True)
        self.ai_button.setToolTip("Ẩn/hiện Chat AI (Ctrl+Alt+I)")
        self.ai_button.clicked.connect(lambda: self._set_ai_visible(not self._ai_visible))
        layout.addWidget(self.ai_button)
        return bar

    def _command_button(
        self, object_name: str, text: str, icon_name: str, tooltip: str, callback
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setText(text)
        button.setProperty("responsiveText", text)
        button.setIcon(icon(icon_name))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setIconSize(QSize(14, 14))
        button.setFixedHeight(29)
        button.setToolTip(tooltip)
        button.clicked.connect(lambda _checked=False: callback())
        return button

    @staticmethod
    def _toolbar_separator() -> QFrame:
        separator = QFrame()
        separator.setObjectName("ToolbarSeparator")
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFixedHeight(24)
        return separator

    def _build_content_area(self) -> QWidget:
        split = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_split = split
        split.setObjectName("WorkspaceSplitter")
        split.setChildrenCollapsible(False)
        split.setHandleWidth(4)

        # ------------------------------------------------- left: project tree
        left_column = QSplitter(Qt.Orientation.Vertical)
        self.left_workspace_column = left_column
        left_column.setObjectName("LeftWorkspaceColumn")
        left_column.setChildrenCollapsible(False)
        left_column.setHandleWidth(4)

        project_panel = PanelFrame("EXPLORER")
        self.project_panel_frame = project_panel
        self.left_panel_menu_button = project_panel.menu_button
        left_menu = QMenu(project_panel.menu_button)
        for label, icon_name, handler in (
            ("Mở tệp…", "fa5s.file", lambda: self._open_file_dialog(False)),
            ("Mở thư mục dự án…", "fa5s.folder-open", self.open_project_dialog),
            ("Lưu tất cả", "fa5s.save", lambda: self.tabs.save_all()),
        ):
            action = QAction(icon(icon_name), label, left_menu)
            action.triggered.connect(lambda _checked=False, h=handler: h())
            left_menu.addAction(action)
        project_panel.menu_button.setMenu(left_menu)
        project_panel.set_content_margins(4, 2, 4, 4)

        self.left_tabs = QTabWidget()
        self.left_tabs.setObjectName("SideTabs")
        self.left_tabs.tabBar().hide()
        self.explorer = ExplorerPanel()
        self.search_panel = ProjectSearchPanel()
        self.left_tabs.addTab(self.explorer, "Explorer")
        self.left_tabs.addTab(self.search_panel, "Search")
        project_panel.add_widget(self.left_tabs)

        # Panel TÀI NGUYÊN đã chuyển sang AssetsStudioWindow (cửa sổ riêng).
        left_column.addWidget(project_panel)
        left_column.setStretchFactor(0, 1)
        left_column.setMinimumWidth(190)

        # ------------------------------------ center: code tabs + bottom panel
        center_column = QSplitter(Qt.Orientation.Vertical)
        self.center_workspace_column = center_column
        center_column.setObjectName("CenterWorkspaceColumn")
        center_column.setChildrenCollapsible(True)
        center_column.setHandleWidth(4)

        editor_host = QFrame()
        editor_host.setObjectName("EditorPanel")
        editor_layout = QVBoxLayout(editor_host)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        self.find_bar = FindReplaceBar()
        editor_layout.addWidget(self.find_bar)
        self.tabs = EditorGroupManager()
        editor_layout.addWidget(self.tabs)

        self.bottom = BottomPanel()
        self.vxpemu_panel = VxpEmuPanel()
        self.bottom.addTab(self.vxpemu_panel, "VXPEMU")
        self.vxpemu_panel.run_requested.connect(lambda: self._run_build_command("run_vxpemu"))
        self.vxpemu_panel.stop_requested.connect(self.runner.stop_vxpemu)
        self.bottom.setCurrentWidget(self.vxpemu_panel)
        self.bottom.console.append("Sẵn sàng — Lua → ARM VXP qua core LuaS30.")

        center_column.addWidget(editor_host)
        center_column.addWidget(self.bottom)
        self.bottom.hide()
        center_column.setSizes([840, 0])
        center_column.setStretchFactor(0, 1)
        center_column.setStretchFactor(1, 0)

        # ----------------------------------------- right: device + assistant
        # THIẾT BỊ sống trong hộp thoại modal gọi từ menu "Công cụ"
        # (_build_device_dialog).  CHAT AI đứng lại trong workspace, là cột
        # thứ ba bên phải trình soạn thảo đúng như Chat của VS Code.
        self._build_device_dialog()
        self._build_ai_dock()

        split.addWidget(left_column)
        split.addWidget(center_column)
        split.addWidget(self.ai_panel_frame)
        split.setSizes([300, 900, 380])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)

        # ---------------------------------------------------- internal wiring
        self.explorer.file_activated.connect(self.tabs.open_file)
        self.explorer.status_message.connect(self.show_status)
        self.search_panel.open_result.connect(self.open_location)
        self.left_tabs.currentChanged.connect(lambda *_: self._update_activity_bar())
        self.find_bar.hide()
        self.tabs.cursor_info_changed.connect(self._update_cursor)
        self.tabs.file_saved.connect(self._file_saved)
        self.tabs.file_opened.connect(lambda *_: self._schedule_workspace_save())
        self.tabs.current_editor_changed.connect(self._current_editor_changed)
        self.tabs.diagnostics_changed.connect(self._diagnostics_changed)
        self.tabs.go_to_definition_requested.connect(self.go_to_definition)
        self.tabs.request_find.connect(self._show_find)
        self.bottom.open_location.connect(self.open_location)
        self.bottom.ask_ai.connect(self._ask_ai_about_problems)
        self.bottom.close_requested.connect(lambda: self._set_console_visible(False))
        self.bottom.terminal.status_message.connect(self.show_status)
        self.bottom.terminal.command_finished.connect(self.ai_chat.on_shell_command_finished)
        self.ai_chat.status_message.connect(self.show_status)
        self.ai_chat.visibility_requested.connect(self._set_ai_visible)
        self.ai_chat.set_active_editor_provider(self._active_editor_context)
        self.ai_chat.set_shell_runner(self._run_ai_shell)
        self.ai_chat.set_shell_stopper(self._stop_ai_shell)
        self.ai_chat.set_run_app(self._run_and_capture_app)
        self.ai_chat.set_run_app_stopper(self._stop_ai_run_app)
        self.ai_chat.set_problems_provider(self._ai_problems_snapshot)
        self.ai_chat.set_problems_rows_provider(lambda: self.bottom.problems._rows())
        self.ai_chat.set_open_location_provider(self._ai_open_location)
        self.ai_chat.changes_proposed.connect(self._prepare_ai_changes)
        self.ai_chat.review_changes_requested.connect(self._review_ai_changes)
        self.ai_chat.apply_changes_requested.connect(self._apply_ai_changes)
        self.ai_chat.reject_changes_requested.connect(self._reject_ai_changes)
        for pane in (split, left_column, center_column):
            pane.splitterMoved.connect(lambda *_: self._schedule_workspace_save())
        self._update_activity_bar()
        return split

    def _build_device_dialog(self) -> None:
        """Hộp thoại THIẾT BỊ · VXPEMU (menu Công cụ, Ctrl+Alt+D).

        CHAT AI đã chuyển ra cột phải của workspace (_build_ai_dock), nên
        trong dialog chỉ còn panel thiết bị + nút Project Doctor.
        """
        dialog = CustomDialog(
            "THIẾT BỊ · VXPEMU",
            self,
            width=430,
            height=700,
            resizable=True,
            modal=True,
        )
        dialog.hide_footer()
        dialog.set_close_handler(dialog.hide)
        self.device_dialog = dialog

        device_panel = PanelFrame("THIẾT BỊ · VXPEMU")
        self.device_panel_frame = device_panel
        self.emulator_view = EmulatorView()
        self.emulator_view.run_last_requested.connect(self._run_last_build)
        self.emulator_view.stop_requested.connect(self.runner.stop_vxpemu)
        self.emulator_view.open_build_folder_requested.connect(self._open_build_folder)
        self.emulator_view.open_emulator_folder_requested.connect(self._open_emulator_folder)
        device_panel.add_widget(self.emulator_view)
        self.doctor_button = QPushButton("Mở Project Doctor")
        self.doctor_button.setObjectName("SecondaryAction")
        self.doctor_button.setIcon(icon("fa5s.stethoscope"))
        self.doctor_button.clicked.connect(self._open_project_doctor)
        device_row = QWidget()
        device_row_layout = QHBoxLayout(device_row)
        device_row_layout.setContentsMargins(0, 0, 0, 0)
        device_row_layout.addWidget(self.doctor_button)
        device_panel.add_widget(device_row)

        device_panel.setMinimumWidth(220)
        dialog.add_body_widget(device_panel, 1)

    def _build_ai_dock(self) -> None:
        """CHAT AI — cột thứ ba của workspace, kiểu panel Chat của VS Code."""
        # AIChatView tự mang header "AI Agent" + tab riêng nên bỏ header PanelFrame.
        ai_panel = PanelFrame("CHAT AI", show_header=False)
        ai_panel.set_content_margins(0, 0, 0, 0)
        self.ai_panel_frame = ai_panel
        self.ai_chat = AIChatView(self.engine_root)
        ai_panel.add_widget(self.ai_chat)
        ai_panel.setMinimumWidth(280)
        # Đóng/mở bằng Ctrl+Alt+I, nút trên title bar hoặc "Công cụ → Chat AI".
        ai_panel.setVisible(False)

    def _open_device_dialog(self) -> None:
        self.device_dialog.show()
        self.device_dialog.raise_()
        self.device_dialog.activateWindow()

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(30)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        ready_icon = QLabel()
        ready_icon.setPixmap(icon("fa5s.circle", "#4BD37B").pixmap(9, 9))
        layout.addWidget(ready_icon)
        self.engine_state_label = QLabel("VXP Ready")
        layout.addWidget(self.engine_state_label)
        self.bottom_panel_button = QToolButton()
        self.bottom_panel_button.setObjectName("StatusBottomPanelButton")
        self.bottom_panel_button.setIcon(icon("fa5s.terminal"))
        self.bottom_panel_button.setIconSize(QSize(12, 12))
        self.bottom_panel_button.setToolTip("Hiện/ẩn Console, Problems, Terminal, HEX và VXPEmu (Ctrl+J)")
        self.bottom_panel_button.setFixedSize(25, 24)
        self.bottom_panel_button.setProperty("panelVisible", False)
        self.bottom_panel_button.clicked.connect(self._toggle_console_panel)
        layout.addWidget(self.bottom_panel_button)
        self.status_cursor = QLabel("")
        self.status_cursor.setObjectName("StatusPath")
        layout.addWidget(self.status_cursor)

        self.task_progress = BottomTaskProgress(self.root_frame)
        self.task_progress.attach_to_host(self.root_frame)
        self.task_progress.open_requested.connect(self._show_run_session)
        self.task_progress.cancel_requested.connect(self.runner.stop)
        self.task_progress.hide()

        self.status_path = QLabel("(chưa mở dự án)")
        self.status_path.setObjectName("StatusPath")
        layout.addWidget(self.status_path, 1)

        self.language_badge = QLabel("Lua 5.1")
        self.encoding_badge = QLabel("UTF-8")
        self.encoding_badge.setToolTip("Mã hóa tệp mà Studio đọc/ghi")
        self.indent_badge = QLabel("Spaces: 4")
        self.indent_badge.setToolTip("Kiểu thụt lề của trình soạn thảo")
        self.core_badge = QLabel("core lua-s30")
        self.target_badge = QLabel("MRE VXP")
        self.native_badge = QLabel("ARM + VXPEmu")
        self.app_id_badge = QLabel("App ID –")
        self.app_id_badge.setObjectName("StatusAppId")
        self.version_badge = QLabel(f"v{self.version_text}" if self.version_text else "")
        # Thứ tự quyết định nhãn nào còn lại khi cửa sổ hẹp: App ID luôn giữ lại.
        self._status_optional_widgets = [
            self.encoding_badge, self.indent_badge,
            self.target_badge, self.native_badge, self.language_badge,
            self.app_id_badge, self.core_badge,
        ]
        for widget in (
            self.language_badge, self.encoding_badge, self.indent_badge,
            self.core_badge, self.target_badge,
            self.native_badge, self.app_id_badge, self.version_badge,
        ):
            layout.addWidget(widget)
        return bar

    # ============================================================ navigation
    def _show_home(self) -> None:
        self.home_page.set_projects(self.project_library.scan())
        self.stack.setCurrentWidget(self.home_page)
        self.title_bar.set_home_mode(True)
        self._set_console_action_visible(False)

    def _enter_editor(self) -> bool:
        if self.stack.currentWidget() is self.editor_page:
            return True
        if not self.session.root:
            return False
        self.stack.setCurrentWidget(self.editor_page)
        self.title_bar.set_home_mode(False)
        self.title_bar.set_project_name(f"{Path(self.session.root).name} • Lua VXP")
        self._update_activity_bar()
        return True

    def show_initial(self) -> None:
        self.window_state_controller.show_initial()

    def set_window_visible(self, visible: bool) -> None:
        if visible:
            self.window_state_controller.show_window()
        else:
            self.window_state_controller.hide_window()

    def restore_from_title_drag(
        self, global_position: QPoint, horizontal_ratio: float, local_y: int
    ) -> None:
        self.window_state_controller.restore_from_title_drag(global_position, horizontal_ratio, local_y)

    # ============================================================ project IO
    def create_project_from_template(self) -> None:
        if not self.tabs.close_file_tabs():
            return
        dialog = MediaTekMREConfigDialog(self)
        dialog.set_project_root_preview(str(self.session.default_projects_root))
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        config = dialog.configuration()
        name = config.app_name
        try:
            target = self.session.project_path(name)
            if target.exists():
                raise FileExistsError(target)
            info = self.session.create_project(
                name,
                metadata=config.project_metadata(),
                sdk_metadata=config.sdk_metadata(),
            )
        except FileExistsError as exc:
            NoticeDialog("Dự án đã tồn tại", f"Đã có dự án trùng tên:\n{exc}", self, error=True).exec()
            return
        except (OSError, ValueError) as exc:
            NoticeDialog("Không thể tạo dự án", str(exc), self, error=True).exec()
            return
        self._switch_project(info.root)
        try:
            descriptor = json.loads(
                (info.root / "project.json").read_text(encoding="utf-8-sig")
            )
            appid = descriptor.get("appid")
        except Exception:
            appid = None
        self.show_status(
            f"Project created: {info.root}"
            + (f" | AppID {appid}" if appid else "")
            + f" | {config.chipset_id} | {config.screen_width}x{config.screen_height}"
        )

    def open_project_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Mở thư mục dự án LuaS30",
            str(self.session.root or self.session.default_projects_root),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self._switch_project(Path(folder))

    def _open_file_dialog(self, _unused: bool = False) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file",
            str(self.session.root or self.session.default_projects_root),
            "Source Files (*.lua *.c *.h *.json *.txt *.md);;All Files (*)",
        )
        if path:
            self._enter_editor()
            self.tabs.open_file(path)

    def _open_record_from_home(self, record: ProjectRecord) -> None:
        root = Path(record.root)
        if not root.is_dir():
            NoticeDialog(
                "Không tìm thấy dự án",
                "Thư mục dự án đã bị di chuyển hoặc xóa khỏi ổ đĩa.",
                self,
                error=True,
            ).exec()
            self.home_page.set_projects(self.project_library.scan())
            return
        self._switch_project(root)

    def _rename_from_home(self, record: ProjectRecord) -> None:
        source = Path(record.root)
        new_name, ok = TextInputDialog.get_text(
            self, "Đổi tên dự án", "Tên project mới", text=source.name
        )
        if not ok or not new_name.strip():
            return
        is_current = bool(self.session.root and source.resolve() == self.session.root)
        if is_current and not self.tabs.close_file_tabs():
            return
        try:
            destination = self.project_library.rename(source, new_name.strip())
            if is_current:
                self.session.open_project(destination)
                self._apply_project(destination, open_main=False)
            self.show_status(f"Project renamed: {destination.name}")
        except Exception as exc:
            NoticeDialog("Không thể đổi tên", str(exc), self, error=True).exec()
        self.home_page.set_projects(self.project_library.scan())

    def _remove_from_home(self, record: ProjectRecord) -> None:
        source = Path(record.root)
        if not ConfirmDialog.ask(
            "Xóa project",
            f"Xóa toàn bộ thư mục dự án khỏi ổ đĩa?\n\n{source}",
            self,
            confirm_text="Xóa",
        ):
            return
        is_current = bool(self.session.root and source.resolve() == self.session.root)
        if is_current and not self.tabs.close_file_tabs():
            return
        try:
            self.project_library.delete(source)
            if is_current:
                self.session.close_project()
                self._clear_project_chrome()
                self._show_home()
            self.show_status(f"Project deleted: {source.name}")
        except Exception as exc:
            NoticeDialog("Không thể xóa", str(exc), self, error=True).exec()
        self.home_page.set_projects(self.project_library.scan())

    def _close_project(self) -> None:
        if not self.session.root:
            self._show_home()
            return
        if not self.tabs.close_file_tabs():
            return
        self.session.close_project()
        self._clear_project_chrome()
        self._show_home()
        self.show_status("Project closed")

    def _switch_project(self, path: Path, open_main: bool = True) -> None:
        if not self.tabs.close_file_tabs():
            return
        try:
            info = self.session.open_project(path)
        except (OSError, ValueError) as exc:
            NoticeDialog("Không thể mở dự án", str(exc), self, error=True).exec()
            return
        self._apply_project(info.root, open_main=open_main)
        self._enter_editor()
        self.show_status(f"Project opened: {info.root}")

    def _apply_project(self, root: Path, open_main: bool = False) -> None:
        root = Path(root).resolve()
        self._project_meta = self._read_project_meta(root)
        self.explorer.set_project_root(root)
        self.search_panel.set_root(root)
        self.index.set_root(root)
        self.bottom.terminal.set_project_root(root)
        self.ai_chat.set_project_root(root)
        self.assets_studio.set_project(root)
        self.emulator_view.set_project(root)
        doctor = self.tabs.tool_widget("project-doctor")
        if isinstance(doctor, ProjectDoctorView):
            doctor.set_project(root)
        manager = self.tabs.tool_widget("projects")
        if isinstance(manager, ProjectManagerView):
            manager.set_current_project(root)
        self._load_last_manifest(root)
        if self.last_manifest:
            self.emulator_view.set_manifest(self.last_manifest)
        self.title_bar.set_project_name(f"{root.name} • Lua VXP")
        self.project_panel_frame.title_label.setText(f"EXPLORER - {root.name}")
        self.status_path.setText(str(root))
        self.status_path.setToolTip(str(root))
        self._update_badges()
        if open_main:
            main_lua = root / "main.lua"
            if main_lua.is_file():
                self.tabs.open_file(main_lua)
        self.bottom.console.append(
            f"Project indexed: {root.name} ({len(self.index.names())} symbols)"
        )
        self._schedule_workspace_save()

    def _clear_project_chrome(self) -> None:
        self._project_meta = {}
        self.explorer.clear_project()
        self.search_panel.clear_root()
        self.index.set_root(None)
        self.bottom.terminal.set_project_root(None)
        self.ai_chat.set_project_root(None)
        self.assets_studio.set_project(None)
        self.emulator_view.set_project(None)
        self.last_manifest = {}
        self.title_bar.set_project_name("")
        self.project_panel_frame.title_label.setText("EXPLORER")
        self.status_path.setText("(chưa mở dự án)")
        self._update_badges()

    @staticmethod
    def _read_project_meta(root: Path) -> dict:
        descriptor = root / "project.json"
        if not descriptor.is_file():
            return {}
        try:
            payload = json.loads(descriptor.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _update_badges(self) -> None:
        meta = self._project_meta
        appid = meta.get("appid")
        self.app_id_badge.setText(f"App ID {appid}" if appid else "App ID –")
        width = meta.get("screen_width") or meta.get("width")
        height = meta.get("screen_height") or meta.get("height")
        target = str(meta.get("runtime_target") or "MRE VXP")
        if width and height:
            self.target_badge.setText(f"MRE VXP {width}×{height}")
        else:
            self.target_badge.setText(target)

    def _load_last_manifest(self, project: Path) -> None:
        manifest = project / "build" / "sync_manifest.json"
        if not manifest.is_file():
            self.last_manifest = {}
            return
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["_manifest_path"] = str(manifest)
            self.last_manifest = data
        except Exception:
            self.last_manifest = {}

    # ============================================================== tool tabs
    def _open_designer(self) -> UIDesignerView | None:
        """UI Designer không còn là tool tab — nó ở trong AssetsStudioWindow."""
        if not self._require_project("UI Designer"):
            return None
        self._enter_editor()
        self.assets_studio.show_studio()
        return self.assets_studio.designer

    def _designer_log(self, message: str) -> None:
        text = (message or "").strip()
        if not text:
            return
        self._append_console(text)
        self.engine_state_label.setText(text.splitlines()[0])
        QTimer.singleShot(2400, self._restore_ready)

    def _open_settings(self) -> SettingsView:
        def factory():
            view = SettingsView(
                self.engine_root,
                startup_mode=self._startup_mode,
                compiler_profile=self._compiler_profile,
                toolchain_root=self._toolchain_root,
                compat_profile=self._compat_profile,
                mre_sdk_root=self._mre_sdk_root,
            )
            view.startup_mode_changed.connect(self._set_startup_mode)
            view.compiler_profile_changed.connect(self._set_compiler_profile)
            view.toolchain_root_changed.connect(self._set_toolchain_root)
            view.compat_profile_changed.connect(self._set_compat_profile)
            view.mre_sdk_root_changed.connect(self._set_mre_sdk_root)
            view.device_imsi_changed.connect(self._set_device_imsi)
            return view

        self._enter_editor()
        view = self.tabs.open_tool_tab("settings", "Cài đặt", factory, icon("fa5s.cog"))
        if isinstance(view, SettingsView):
            view.set_startup_mode(self._startup_mode)
            view.set_compiler_profile(self._compiler_profile)
            view.set_toolchain_root(self._toolchain_root)
            view.set_compat_profile(self._compat_profile)
            view.set_mre_sdk_root(self._mre_sdk_root)
        return view

    def _open_projects_tab(self) -> ProjectManagerView | None:
        def factory():
            view = ProjectManagerView(self.project_library)
            view.open_project_requested.connect(self._switch_project)
            view.new_project_requested.connect(self.create_project_from_template)
            view.duplicate_project_requested.connect(self._duplicate_managed_project)
            view.rename_project_requested.connect(self._rename_managed_project)
            view.delete_project_requested.connect(self._delete_managed_project)
            view.status_message.connect(self.show_status)
            view.set_current_project(self.session.root)
            return view

        self._enter_editor()
        view = self.tabs.open_tool_tab("projects", "Project Hub", factory, icon("fa5s.folder"))
        if isinstance(view, ProjectManagerView):
            view.set_current_project(self.session.root)
            view.refresh()
        return view

    def _open_project_doctor(self) -> ProjectDoctorView | None:
        if not self._require_project("Project Doctor"):
            return None
        self._enter_editor()
        view = self.tabs.open_tool_tab(
            "project-doctor", "Project Doctor",
            lambda: ProjectDoctorView(self.engine_root, self.session.root),
            icon("fa5s.stethoscope"),
        )
        if isinstance(view, ProjectDoctorView):
            view.set_project(self.session.root)
        return view

    def _open_compat_matrix(self) -> CompatMatrixView | None:
        def factory():
            view = CompatMatrixView()
            view.run_requested.connect(self._start_compat_matrix)
            return view

        self._enter_editor()
        view = self.tabs.open_tool_tab(
            "compat-matrix", "Runtime Compatibility", factory, icon("fa5s.th")
        )
        report = self.engine_root / "build" / "runtime_compat_matrix" / "runtime_compat_matrix.json"
        if isinstance(view, CompatMatrixView) and report.is_file():
            try:
                view.load_report(report)
            except Exception as exc:
                view.append_output(f"Could not load previous matrix: {exc}")
        return view

    def _start_compat_matrix(self) -> None:
        view = self._open_compat_matrix()
        if self.compat_matrix_service.active:
            self.show_status("Compatibility matrix is already running.")
            return
        if isinstance(view, CompatMatrixView):
            view.set_running()
        try:
            self.compat_matrix_service.start()
        except Exception as exc:
            NoticeDialog("Runtime Compatibility Matrix", str(exc), self, error=True).exec()

    def _compat_output(self, text: str) -> None:
        self._append_console(text)
        view = self.tabs.tool_widget("compat-matrix")
        if isinstance(view, CompatMatrixView):
            view.append_output(text)

    def _compat_finished(self, success: bool, exit_code: int, report_path: Path) -> None:
        view = self.tabs.tool_widget("compat-matrix")
        if success:
            if isinstance(view, CompatMatrixView):
                try:
                    view.load_report(report_path)
                except Exception as exc:
                    view.append_output(f"Report load failed: {exc}")
            self.show_status("Runtime compatibility matrix completed")
        else:
            if isinstance(view, CompatMatrixView):
                view.append_output(f"Matrix failed with exit code {exit_code}")
            self.show_status(f"Compatibility matrix failed ({exit_code})")

    def _open_toolchain_doctor(self) -> ToolchainDoctorView:
        def factory():
            view = ToolchainDoctorView(self.engine_root)
            view.set_toolchain(self._toolchain_root, self._compiler_profile)
            return view

        self._enter_editor()
        view = self.tabs.open_tool_tab(
            "toolchain-doctor", "Toolchain Doctor", factory, icon("fa5s.wrench")
        )
        if isinstance(view, ToolchainDoctorView):
            view.set_toolchain(self._toolchain_root, self._compiler_profile)
        return view

    def _populate_extensions_menu(self, menu: QMenu) -> None:
        """Nạp lại menu 'Tiện ích mở rộng' mỗi lần mở — thêm thư mục extension
        mới vào engine_root/extensions là xuất hiện ngay, không cần khởi động lại."""
        menu.clear()
        store = menu.addAction("Cửa hàng tiện ích mở rộng…")
        store.setIcon(icon("fa5s.th"))
        store.triggered.connect(
            lambda _checked=False: self._open_extensions_market()
        )
        menu.addSeparator()
        installed = self.extension_service.discover(refresh=True)
        if not installed:
            empty = menu.addAction("(Chưa có tiện ích nào trong thư mục extensions/)")
            empty.setEnabled(False)
            return
        for manifest in installed:
            action = menu.addAction(f"{manifest.name}  ·  v{manifest.version}")
            action.setIcon(icon(manifest.icon))
            action.setToolTip(manifest.description or manifest.id)
            action.triggered.connect(
                lambda _checked=False, ext_id=manifest.id: self._open_extension(ext_id)
            )

    def _open_extensions_market(self):
        """Tab công cụ liệt kê mọi extension đã cài dạng card (như ảnh mẫu)."""
        from app.views.extension_market_view import ExtensionMarketView

        def factory():
            return ExtensionMarketView(
                self.extension_service,
                on_open=self._open_extension,
                on_change=self._refresh_activity_extensions,
            )

        self._enter_editor()
        return self.tabs.open_tool_tab(
            "extensions-market",
            "Tiện ích mở rộng",
            factory,
            icon("fa5s.puzzle-piece"),
        )

    def _open_extension(self, extension_id: str):
        manifest = self.extension_service.manifest(extension_id)
        if manifest is None:
            self.app_toast.show_message(
                f"Không tìm thấy tiện ích mở rộng {extension_id!r} trong extensions/."
            )
            return None
        if manifest.requires_project and not self._require_project(manifest.name):
            return None

        def factory():
            from app.views.extension_host_view import ExtensionHostView

            return ExtensionHostView(
                manifest,
                project_root_provider=lambda: self.session.root,
                status_reporter=self.show_status,
                on_files_written=lambda _paths: self._refresh_project_assets(),
            )

        self._enter_editor()
        view = self.tabs.open_tool_tab(manifest.tool_key, manifest.name, factory, icon(manifest.icon))
        if hasattr(view, "focus_webview"):
            view.focus_webview()
        return view

    def _require_project(self, feature: str) -> bool:
        if self.session.root:
            return True
        self._show_home()
        self.app_toast.show_message(f"Mở một dự án trước khi dùng {feature}.")
        return False

    # ==================================================== settings persistence
    def _set_startup_mode(self, mode: str) -> None:
        mode = str(mode or "welcome")
        if mode not in {"welcome", "project_hub", "empty_editor"}:
            mode = "welcome"
        self._startup_mode = mode
        self._schedule_workspace_save()
        self.show_status(f"Startup screen: {mode} (applies next launch)")

    def _set_compiler_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto", "gcc", "rvds", "ads12"}:
            profile = "auto"
        self._compiler_profile = profile
        self.build_service.set_compiler_profile(profile)
        doctor = self.tabs.tool_widget("toolchain-doctor")
        if isinstance(doctor, ToolchainDoctorView):
            doctor.set_toolchain(self._toolchain_root, profile)
        self._schedule_workspace_save()
        self.show_status(f"Compiler profile: {profile}")

    def _set_toolchain_root(self, root: str) -> None:
        path = Path(root).expanduser().resolve()
        self._toolchain_root = path
        self.build_service.set_toolchain_root(path)
        doctor = self.tabs.tool_widget("toolchain-doctor")
        if isinstance(doctor, ToolchainDoctorView):
            doctor.set_toolchain(path, self._compiler_profile)
        self._schedule_workspace_save()
        self.show_status(f"Toolchain root: {path}")

    def _set_compat_profile(self, profile: str) -> None:
        profile = str(profile or "auto").lower()
        if profile not in {"auto", "standalone", "s30plus-native", "nokia225-rm1011"}:
            profile = "auto"
        self._compat_profile = profile
        self.build_service.set_compat_profile(profile)
        self._schedule_workspace_save()
        self.show_status(f"S30+ compatibility: {profile}")

    def _set_mre_sdk_root(self, root: str) -> None:
        value = str(root or "").strip()
        self._mre_sdk_root = Path(value).expanduser().resolve() if value else None
        self.build_service.set_mre_sdk_root(self._mre_sdk_root)
        self._schedule_workspace_save()
        self.show_status(f"MRE SDK: {self._mre_sdk_root}" if self._mre_sdk_root else "MRE SDK cleared")

    def _set_device_imsi(self, imsi: str) -> None:
        # Sensitive value: memory only, never persisted.
        self.build_service.set_device_imsi(
            "".join(ch for ch in str(imsi or "") if ch.isdigit())
        )
        self.show_status("Nokia IMSI set for this session")

    def _resolve_saved_path(self, value: object, *, default: Path | None = None) -> Path | None:
        if not value:
            return default.resolve() if default else None
        path = Path(str(value)).expanduser()
        if path.exists():
            return path.resolve()
        return default.resolve() if default else None

    def _load_initial_state(self) -> None:
        saved = self.workspace_session.load()
        build_settings = saved.get("build", {}) if isinstance(saved, dict) else {}
        self._compiler_profile = str(build_settings.get("compiler_profile") or "auto")
        if self._compiler_profile not in {"auto", "gcc", "rvds", "ads12"}:
            self._compiler_profile = "auto"
        self._toolchain_root = self._resolve_saved_path(
            build_settings.get("toolchain_root"),
            default=self.engine_root / "toolchain" / "arm-gcc",
        )
        self._compat_profile = str(build_settings.get("compat_profile") or "auto")
        if self._compat_profile not in {"auto", "standalone", "s30plus-native", "nokia225-rm1011"}:
            self._compat_profile = "auto"
        self._mre_sdk_root = self._resolve_saved_path(build_settings.get("mre_sdk_root"))
        self.build_service.set_compiler_profile(self._compiler_profile)
        self.build_service.set_toolchain_root(self._toolchain_root)
        self.build_service.set_compat_profile(self._compat_profile)
        self.build_service.set_mre_sdk_root(self._mre_sdk_root)

        startup = saved.get("startup", {}) if isinstance(saved, dict) else {}
        mode = str(startup.get("mode") or "").strip()
        if mode not in {"welcome", "project_hub", "empty_editor"}:
            mode = "welcome" if bool(startup.get("show_start_page", True)) else "empty_editor"
        self._startup_mode = mode

        project_path = saved.get("project") if isinstance(saved, dict) else None
        restored_project: Path | None = None
        if project_path:
            candidate = Path(str(project_path)).expanduser()
            if candidate.is_dir():
                try:
                    info = self.session.open_project(candidate)
                    self._apply_project(info.root, open_main=False)
                    restored_project = info.root
                except (OSError, ValueError):
                    restored_project = None
        elif startup.get("mode") is None:
            info = self.session.load_initial_project()
            if info is not None:
                self._apply_project(info.root, open_main=False)
                restored_project = info.root

        tool_tabs = [str(k) for k in (saved.get("tool_tabs") or []) if str(k)] if isinstance(saved, dict) else []
        self._restoring_workspace = True
        try:
            if self._startup_mode != "empty_editor":
                for key in tool_tabs:
                    self._restore_tool_tab(key)
        finally:
            self._restoring_workspace = False

        self._restore_workspace_layout_state(saved if isinstance(saved, dict) else {})
        self._activate_startup_mode(bool(restored_project))

    def _activate_startup_mode(self, has_restored_project: bool) -> None:
        if self._startup_mode == "project_hub" and has_restored_project:
            self._enter_editor()
            self._open_projects_tab()
        elif self._startup_mode == "empty_editor" and has_restored_project:
            self._enter_editor()

    def _restore_workspace_layout_state(self, saved: dict) -> None:
        panel = saved.get("panel") if isinstance(saved.get("panel"), dict) else {}
        try:
            height = int(panel.get("height", self._console_last_height))
        except (TypeError, ValueError):
            height = self._console_last_height
        self._console_last_height = max(130, min(height, 1200))
        active_key = str(panel.get("active_key") or "")
        if active_key:
            self.bottom.set_active_key(active_key)
        # Startup policy mirrors VXPEngine: the bottom panel starts hidden;
        # Ctrl+J reveals it again at the remembered height.
        self._console_visible = False
        self.bottom.hide()

        workspace = saved.get("workspace") if isinstance(saved.get("workspace"), dict) else {}
        for name, splitter, minimum in (
            ("sizes", self.workspace_split, self.LEFT_COLUMN_MIN_WIDTH),
            ("left", self.left_workspace_column, 160),
            ("center", self.center_workspace_column, 120),
        ):
            sizes = workspace.get(name)
            if not isinstance(sizes, list) or len(sizes) != splitter.count():
                continue
            try:
                restored = [max(0, int(value)) for value in sizes]
            except (TypeError, ValueError):
                continue
            # A dragged-to-zero pane must never be restored, otherwise the
            # column stays unreachable until sizes are reset by hand.
            if restored and restored[0] < minimum:
                restored[0] = minimum
            splitter.setSizes(restored)

    def _restore_tool_tab(self, key: str) -> bool:
        if key == "settings":
            return self._open_settings() is not None
        if key == "projects":
            return self._open_projects_tab() is not None
        if key == "designer":
            return self._open_designer() is not None
        if key == "project-doctor":
            return self._open_project_doctor() is not None
        if key == "compat-matrix":
            return self._open_compat_matrix() is not None
        if key == "toolchain-doctor":
            return self._open_toolchain_doctor() is not None
        if key.startswith("extension:"):
            return self._open_extension(key.split(":", 1)[1]) is not None
        if key == "extensions-market":
            return self._open_extensions_market() is not None
        return False

    def _schedule_workspace_save(self, *_args) -> None:
        if self._restoring_workspace:
            return
        self._workspace_save_timer.start()

    def _save_workspace_session(self) -> None:
        if self._restoring_workspace:
            return
        open_tabs = self.tabs.session_state() or {}
        tool_keys: list[str] = []
        for group in open_tabs.get("groups", []) if isinstance(open_tabs, dict) else []:
            for entry in group.get("tabs", []) if isinstance(group, dict) else []:
                if isinstance(entry, dict) and entry.get("type") == "tool":
                    key = str(entry.get("key", ""))
                    if key in _PERSISTENT_TOOL_TABS or key.startswith("extension:"):
                        if key not in tool_keys:
                            tool_keys.append(key)
        state = {
            "project": str(self.session.root) if self.session.root else None,
            "tool_tabs": tool_keys,
            "startup": {
                "mode": self._startup_mode,
                "show_start_page": self._startup_mode == "welcome",
                "restore_source_tabs": False,
            },
            "panel": {
                "visible": bool(self._console_visible),
                "height": int(self._console_last_height),
                "active_key": self.bottom.active_key(),
            },
            "workspace": {
                "sizes": self.workspace_split.sizes(),
                "left": self.left_workspace_column.sizes(),
                "center": self.center_workspace_column.sizes(),
            },
            "build": {
                "compiler_profile": self._compiler_profile,
                "toolchain_root": str(self._toolchain_root),
                "compat_profile": self._compat_profile,
                "mre_sdk_root": str(self._mre_sdk_root) if self._mre_sdk_root else None,
            },
        }
        try:
            self.workspace_session.save(state)
        except OSError as exc:
            self.bottom.console.append(f"[SESSION] Could not save workspace: {exc}")

    # ======================================================= project lifecycle
    def _duplicate_managed_project(self, source: Path, new_name: str) -> None:
        source = Path(source).resolve()
        try:
            destination = self.project_library.duplicate(source, new_name)
            manager = self.tabs.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.refresh()
                manager.select_path(destination)
            self.home_page.set_projects(self.project_library.scan())
            self.show_status(f"Project duplicated: {destination.name}")
        except Exception as exc:
            NoticeDialog("Duplicate Project", str(exc), self, error=True).exec()

    def _rename_managed_project(self, source: Path, new_name: str) -> None:
        source = Path(source).resolve()
        is_current = bool(self.session.root and source == self.session.root)
        if is_current and not self.tabs.close_file_tabs():
            return
        try:
            destination = self.project_library.rename(source, new_name)
            if is_current:
                self.session.open_project(destination)
                self._apply_project(destination, open_main=False)
            manager = self.tabs.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.set_current_project(self.session.root)
                manager.select_path(destination)
            self.home_page.set_projects(self.project_library.scan())
            self.show_status(f"Project renamed: {destination.name}")
        except Exception as exc:
            NoticeDialog("Rename Project", str(exc), self, error=True).exec()

    def _delete_managed_project(self, source: Path) -> None:
        source = Path(source).resolve()
        is_current = bool(self.session.root and source == self.session.root)
        if is_current and not self.tabs.close_file_tabs():
            return
        try:
            self.project_library.delete(source)
            if is_current:
                self.session.close_project()
                self._clear_project_chrome()
                self._show_home()
            manager = self.tabs.tool_widget("projects")
            if isinstance(manager, ProjectManagerView):
                manager.set_current_project(self.session.root)
            self.home_page.set_projects(self.project_library.scan())
            self.show_status(f"Project deleted: {source.name}")
        except Exception as exc:
            NoticeDialog("Delete Project", str(exc), self, error=True).exec()

    def _open_current_project_folder(self) -> None:
        if self.session.root:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session.root)))

    def _open_build_folder(self) -> None:
        if not self.session.root:
            return
        build = self.session.root / "build"
        build.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(build)))

    def _open_emulator_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.engine_root / "emulator")))

    def _refresh_project_assets(self) -> None:
        if not self.session.root:
            return
        self.assets.refresh()
        self.explorer.tree.refresh()
        self.index.set_root(self.session.root)
        self.bottom.console.append("[Assets] Cấu trúc dự án đã được cập nhật.")

    # ================================================================ build/run
    def _run_build_command(self, command: str) -> None:
        project = self.session.root
        if not project:
            self._show_home()
            self.app_toast.show_message("Mở một dự án trước khi build/run.")
            return
        if self.runner.is_running:
            self.show_status("A build is already running.")
            return
        if command == "clean":
            if not ConfirmDialog.ask(
                "Clean build", f"Xóa thư mục build đã sinh ra?\n{project / 'build'}", self,
                confirm_text="Xóa",
            ):
                return
            self.task_progress.begin("Clean · dự án Lua")
            self.runner.clean(project)
            self._load_last_manifest(project)
            self.emulator_view.set_project(project)
            return
        if not self.tabs.save_all():
            return
        self.bottom.build_log.clear()
        self._set_console_visible(True)
        self.bottom.setCurrentWidget(self.bottom.build_log)
        if command == "run_vxpemu":
            self.runner.run(project)
        else:
            self.runner.build(project)

    def _select_and_run_target(self, index: int) -> None:
        self._selected_build_target_index = max(0, min(index, len(BUILD_TARGETS) - 1))
        for action_index, action in enumerate(self._build_menu_actions):
            action.setChecked(action_index == self._selected_build_target_index)
        self._update_build_button_label()
        self._run_build_command(BUILD_TARGETS[self._selected_build_target_index][2])

    def _update_build_button_label(self) -> None:
        label = BUILD_TARGETS[self._selected_build_target_index][0]
        short_label = {
            "Build VXP (.vxp)": "VXP",
            "Run VXPEmu (build + autostart)": "Run",
            "Clean build folder": "Clean",
        }.get(label, label)
        self.build_button.setText(f"Build · {short_label}")
        self.build_button.setProperty("responsiveText", f"Build · {short_label}")
        self.build_button.setToolTip(f"Thực thi: {label}")

    def _run_last_build(self) -> None:
        if not self.session.root:
            self.app_toast.show_message("Mở một dự án trước khi chạy lại build.")
            return
        if not self.last_manifest:
            self._load_last_manifest(self.session.root)
        if not self.last_manifest:
            NoticeDialog("Giả lập", "Chưa có build manifest đã xác minh. Hãy Build trước.", self).exec()
            return
        self._launch_manifest(self.last_manifest)

    # ---------------------------------------------------------- runner events
    def _append_console(self, text: str) -> None:
        if not text:
            return
        self._console_pending.append(text)
        if not self._console_flush_timer.isActive():
            self._console_flush_timer.start()

    def _flush_console(self) -> None:
        """Vẽ một lần mọi chunk đã gom — cắt số lần repaint xuống ~16 lần/giây."""
        if not self._console_pending:
            return
        text = "".join(self._console_pending)
        self._console_pending.clear()
        self.bottom.console.append(text)
        self.bottom.build_log.append(text)
        if self.run_session_dialog is not None:
            self.run_session_dialog.append_output(text)

    def _on_runner_started(self, label: str) -> None:
        project_name = Path(self.session.root).name if self.session.root else "Dự án"
        title = f"{label} • {project_name}"
        if self.run_session_dialog is None:
            self.run_session_dialog = RunSessionDialog("Run & Build", self)
            self.run_session_dialog.stop_requested.connect(self.runner.stop)
        self.run_session_dialog.begin(title, show_window=False)
        self.task_progress.begin(title)

    def _on_phase_changed(self, phase: str) -> None:
        self.engine_state_label.setText(phase or "VXP Ready")
        if self.run_session_dialog is not None:
            self.run_session_dialog.set_phase(phase or "Đang chạy")
        if self.task_progress is not None and self.task_progress.isVisible():
            self.task_progress.set_phase(phase or "Đang chạy")

    def _runner_state_changed(self, running: bool) -> None:
        for attr in ("run_button", "build_button", "check_button", "designer_button"):
            button = getattr(self, attr, None)
            if button is not None:
                button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        if not running:
            self.engine_state_label.setText("VXP Ready")

    def _on_runner_finished(self, exit_code: int, success: bool) -> None:
        self._console_flush_timer.stop()
        self._flush_console()   # đẩy nốt output đang gom trước dòng "hoàn tất"
        stopped = bool(getattr(self.runner, "stopped_by_user", False))
        if self.run_session_dialog is not None:
            self.run_session_dialog.set_running(False, None if stopped else success)
            self.run_session_dialog.append_output(
                f"[LuaS30] Tác vụ {'hoàn tất' if success else 'thất bại'} với mã {exit_code}."
            )
        self.task_progress.finish(success, "Hoàn tất" if success else f"Lỗi {exit_code}")
        if success:
            self.bottom.console.append(f"[Build] Hoàn tất. Manifest: {self.session.root / 'build' / 'sync_manifest.json' if self.session.root else ''}")
        else:
            self.bottom.console.append(f"[Build] Tác vụ thất bại với mã {exit_code}.")
        self._schedule_workspace_save()
        # Build thất bại khi đang chạy thử cho Chat AI/`/run`: báo kết quả về chat.
        if self._ai_run_active and not success:
            self._report_ai_run(False, f"Biên dịch thất bại (mã {exit_code}). Xem tab Build Log.")

    def _project_structure_changed(self, project_path: str) -> None:
        if not project_path:
            return
        if self.session.root and Path(project_path).resolve() == self.session.root:
            self._refresh_project_assets()
        self.home_page.set_projects(self.project_library.scan())

    def _on_vxpemu_output(self, message: str) -> None:
        self.vxpemu_panel.append_log(message)

    def _on_vxpemu_started(self, artifact: str, pid: int) -> None:
        self.vxpemu_panel.process_started(artifact, pid)
        self.bottom.setCurrentWidget(self.vxpemu_panel)
        self._set_console_visible(True)
        if pid and os.name == "nt":
            manifest = self.runner.last_manifest or {}
            loaded = str(manifest.get("emulated_vxp") or artifact)
            window = self._vxp_phone_window()
            width = int(self._project_meta.get("screen_width") or 240)
            height = int(self._project_meta.get("screen_height") or 320)
            window.set_orientation("landscape" if width > height else "portrait")
            window.attach_process(loaded, pid)
        # Đang chạy thử cho Chat AI/`/run`: chờ khung hình boot ổn định rồi chụp.
        if self._ai_run_active and not self._ai_run_started:
            self._ai_run_started = True
            QTimer.singleShot(2600, self._ai_capture_and_report)

    def _on_vxpemu_stopped(self, code: int) -> None:
        self.vxpemu_panel.process_stopped(code)
        if self._vxp_emu_window is not None and self._vxp_emu_window.running:
            self._vxp_emu_window.process_stopped(code)
        # Giả lập chết/trước khi kịp chụp: báo thất bại nếu chưa báo.
        if self._ai_run_active and not self._ai_run_reported:
            self._report_ai_run(False, "Giả lập dừng trước khi kịp chụp ảnh kiểm tra.")

    def _on_emulator_state_label(self, state: str) -> None:
        self.emulator_view.set_state(state)
        if state in {"Launching", "Running"}:
            self.engine_state_label.setText(f"VXPEmu · {state}")

    def _on_emulator_launched(self, manifest: object) -> None:
        if not isinstance(manifest, dict):
            return
        self.last_manifest = dict(manifest)
        self.emulator_view.set_manifest(manifest)
        vxp = Path(str(manifest.get("vxp", ""))).expanduser()
        if vxp.is_file():
            self.bottom.hex_view.set_file(vxp)
        self.show_status("Emulator started with SHA-verified VXP / HEX loaded")

    def _launch_manifest(self, manifest: dict) -> None:
        if not manifest:
            NoticeDialog("Giả lập", "Build kết thúc nhưng không có sync manifest.", self, error=True).exec()
            return
        vxp = Path(str(manifest.get("vxp", ""))).expanduser()
        if vxp.is_file():
            self.bottom.show_hex(vxp)
            self._set_console_visible(True)
        try:
            self.emulator_service.launch_manifest(manifest)
        except Exception as exc:
            self._append_console(f"[VXPEmu] ✗ {exc}")
            NoticeDialog("Giả lập", str(exc), self, error=True).exec()

    def _vxp_phone_window(self) -> VxpEmuWindow:
        if self._vxp_emu_window is None:
            window = VxpEmuWindow(self)
            window.stop_requested.connect(self.runner.stop_vxpemu)
            window.restart_requested.connect(self._run_last_build)
            window.load_requested.connect(self._launch_vxp_file)
            self._vxp_emu_window = window
        return self._vxp_emu_window

    def _launch_vxp_file(self, path: str) -> None:
        vxp = Path(path).expanduser().resolve()
        if not vxp.is_file():
            self._append_console(f"[EMU ERROR] VXP not found: {vxp}")
            return
        try:
            digest = hashlib.sha256(vxp.read_bytes()).hexdigest().upper()
        except OSError as exc:
            self._append_console(f"[EMU ERROR] Cannot hash VXP: {exc}")
            return
        fd, name = tempfile.mkstemp(prefix="luas30_emu_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"vxp": str(vxp), "vxp_sha256": digest}, fh)
        self._launch_manifest({
            "vxp": str(vxp),
            "vxp_sha256": digest,
            "_manifest_path": name,
        })

    # ------------------------------------------------------ environment tools
    def _check_environment(self) -> None:
        self.runner.check_environment(self.session.root)

    def _on_environment_checked(self, report: dict) -> None:
        required = list(report.get("missing_required", []))
        optional = list(report.get("missing_optional", []))
        success = not required
        if self.run_session_dialog is not None and not self.runner.is_running:
            self.run_session_dialog.set_running(False, success)
        self.task_progress.finish(success, "Sẵn sàng" if success else "Thiếu môi trường")
        for entry in required + optional:
            self.bottom.console.append(f"[Setup] ✗ Thiếu {entry.get('title')}: {entry.get('hint') or ''}")
        if not required and not optional:
            self.app_toast.show_message("Môi trường lập trình và thư viện đã sẵn sàng.")
            return
        if not required:
            self.app_toast.show_message(
                "Môi trường đã đủ thành phần bắt buộc; một số thành phần tùy chọn còn thiếu.",
                timeout_ms=9000,
            )
            return
        details = "\n".join(
            f"• {entry.get('title')} — {entry.get('hint') or ''}" for entry in required
        )
        NoticeDialog(
            "Thiếu môi trường bắt buộc",
            f"Các thành phần sau cần được cài đặt:\n\n{details}\n\n"
            "Dùng menu Trợ giúp → Kiểm tra & cập nhật môi trường… để cài tự động.",
            self,
            error=True,
        ).exec()

    def _update_environment(self) -> None:
        """Run tools/dependency_manager to refresh Python libs / resources."""
        script = resolve_script(self.engine_root / "tools", "dependency_manager")
        if not script.is_file():
            NoticeDialog("Update Environment", "Không thấy dependency_manager trong tools/.", self, error=True).exec()
            return
        if getattr(self, "_env_update_proc", None) is not None:
            return
        from PySide6.QtCore import QProcess

        proc = QProcess(self)
        self._env_update_proc = proc
        proc.setWorkingDirectory(str(self.engine_root))
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.setProcessEnvironment(utf8_qprocess_environment())
        args = [
            str(script),
            "--requirements", str(self.engine_root / "requirements-studio.txt"),
            "--python", tool_python(self.engine_root),
            "--mode", "online",
            "--force",
        ]
        self._set_console_visible(True)
        self.bottom.show_console()
        self.bottom.console.append("[ENV] Checking and updating environment libraries…")
        proc.readyReadStandardOutput.connect(
            lambda: self._append_console(decode_process_bytes(proc.readAllStandardOutput()))
        )

        def _done(code: int, _status) -> None:
            self._env_update_proc = None
            if code == 0:
                self.bottom.console.append("[ENV] Environment libraries are up to date.")
                self.show_status("Environment libraries OK")
            else:
                self.bottom.console.append(f"[ENV] Update finished with exit code {code}.")
                self.show_status(f"Environment update exit {code}")
            proc.deleteLater()

        proc.finished.connect(_done)
        proc.start(tool_python(self.engine_root), args)
        if not proc.waitForStarted(3000):
            self._env_update_proc = None
            self.bottom.console.append("[ENV] Unable to start dependency manager.")
            proc.deleteLater()

    def _run_first_run_setup(self, force: bool = False) -> None:
        from app.views.setup_dialog import SetupDialog

        try:
            dialog = SetupDialog(self.engine_root, self.version_text or "dev", self, force=force)
            dialog.setup_completed.connect(lambda _ok: self.show_status("Environment setup finished"))
            dialog.exec()
        except Exception as exc:
            self.show_status(f"Không mở được thiết lập lần đầu: {exc}")

    def _maybe_first_run_setup(self) -> None:
        try:
            from app.services.environment_setup import is_first_run

            if is_first_run(self.version_text or "dev"):
                self._run_first_run_setup()
        except Exception as exc:
            self.show_status(f"Không thể chạy thiết lập lần đầu: {exc}")

    # ================================================================== editor
    def _dispatch_focused_editor_method(self, method_name: str) -> None:
        editor = self.tabs.current_editor()
        target = editor or QApplication_focus(self)
        method = getattr(target, method_name, None) if target is not None else None
        if callable(method):
            method()

    def _current_editor_changed(self, editor) -> None:
        self.find_bar.set_editor(editor)
        if editor is not None:
            editor.completion.set_project_symbols(self.index.names())

    def _file_saved(self, path: Path) -> None:
        self.index.index_file(path)
        for index in range(self.tabs.count()):
            editor = self.tabs.editor_at(index)
            if editor is not None:
                editor.completion.set_project_symbols(self.index.names())
        self.show_status(f"Saved: {path.name}")
        self._schedule_workspace_save()

    def _diagnostics_changed(self, path, diagnostics) -> None:
        self.bottom.problems.set_diagnostics(path, diagnostics)
        index = self.bottom.indexOf(self.bottom.problems)
        errors = sum(1 for d in diagnostics if getattr(d.severity, "value", "") == "error")
        warnings = sum(1 for d in diagnostics if getattr(d.severity, "value", "") == "warning")
        self.bottom.setTabText(
            index, f"PROBLEMS ({errors + warnings})" if (errors or warnings) else "PROBLEMS"
        )
        # Nén nhịp: nếu Chat AI đang có thẻ lỗi sống, làm tươi nó theo trạng thái
        # vừa phân tích lại (lỗi biến mất -> ✓ Đã sửa, lỗi mới -> thêm vào).
        if self.ai_chat.has_problem_card():
            self._ai_problem_timer.start()

    def _refresh_ai_problem_card(self) -> None:
        try:
            self.ai_chat.refresh_problem_card()
        except Exception:
            pass

    def _update_cursor(self, line: int, column: int, selected: int) -> None:
        text = f"Ln {line}, Col {column}"
        self.status_cursor.setText(text + (f" ({selected})" if selected else ""))

    def go_to_definition(self, symbol: str, current_path) -> None:
        found = self.index.find_definition(symbol, current_path)
        if not found:
            self.show_status(f"Definition not found: {symbol}")
            return
        self.open_location(found.path, found.line, found.column)
        self.show_status(f"Definition: {found.name} — {found.path.name}:{found.line}")

    def open_location(self, path, line: int, column: int = 1) -> None:
        self._enter_editor()
        editor = self.tabs.open_file(path)
        if editor is not None:
            editor.goto_line(line, column)

    def _ai_open_location(self, path, line: int, column: int = 1) -> None:
        """Chat AI bấm một lỗi trong thẻ 'cần sửa' -> mở đúng tệp:dòng (Antigravity).

        Chat trả về đường dẫn tuyệt đối từ bảng PROBLEMS; suy lại theo gốc dự án
        nếu vì lý do nào đó nó là tương đối, rồi nhảy tới vị trí lỗi.
        """
        p = Path(str(path))
        if not p.is_absolute() and self.session.root:
            p = self.session.root / p
        self.open_location(p, int(line or 1), int(column or 1))

    def _show_find(self, replace: bool) -> None:
        editor = self.tabs.current_editor()
        if editor is None:
            return
        seed = editor.textCursor().selectedText().replace("\u2029", " ")
        self.find_bar.set_editor(editor)
        self.find_bar.show_find(replace, seed)

    # ==================================================================== AI
    def _set_ai_visible(self, visible: bool) -> None:
        self._ai_visible = bool(visible)
        self.ai_panel_frame.setVisible(self._ai_visible)
        self.ai_chat.setVisible(self._ai_visible)
        if self._ai_visible:
            self.ai_chat.show()
            # Lần đầu mở (hoặc sizes cũ còn 0): dành cho chat bề rộng kiểu
            # VS Code ~380px, không để nó bị bóp sát mép phải.
            sizes = self.workspace_split.sizes()
            if len(sizes) >= 3 and sizes[2] < 280:
                left = sizes[0] or 300
                total = sum(sizes) or 1200
                self.workspace_split.setSizes(
                    [left, max(420, total - left - 380), 380])
        if hasattr(self, "ai_toggle_action"):
            self.ai_toggle_action.blockSignals(True)
            self.ai_toggle_action.setChecked(self._ai_visible)
            self.ai_toggle_action.blockSignals(False)
        self.ai_button.setChecked(self._ai_visible)
        self._update_activity_bar()
        self._schedule_workspace_save()

    def _active_editor_context(self):
        editor = self.tabs.current_editor()
        if not editor:
            return None, ""
        return editor.path, editor.toPlainText()

    def _run_ai_shell(self, command: str, cwd=None) -> bool:
        self.bottom.show_terminal()
        self._set_console_visible(True)
        return self.bottom.terminal.run_ai_command(command, cwd)

    def _stop_ai_shell(self) -> bool:
        return self.bottom.terminal.cancel_ai_command()

    # ------------------------------------------------  Chat AI / `/run` smoke test
    def _run_and_capture_app(self, reason: str = "") -> bool:
        """Build dự án đang mở + chạy VXPEmu screen-only cho Chat AI / `/run`.

        Trả về True nếu pipeline đã khởi động. Kết quả thật (kèm ảnh chụp khói)
        được gửi ngược về `AIChatView.on_run_app_finished` qua `_report_ai_run`
        khi khung hình sẵn sàng hoặc khi build/giả lập lỗi.
        """
        if self._ai_run_active or self.runner.is_running:
            return False
        project = self.session.root
        if not project:
            return False
        if not self.tabs.save_all():
            return False
        self._ai_run_active = True
        self._ai_run_started = False
        self._ai_run_reported = False
        self._ai_run_attempts = 0
        self._ai_run_reason = str(reason or "")
        self.bottom.build_log.clear()
        self._set_console_visible(True)
        self.bottom.setCurrentWidget(self.bottom.build_log)
        return bool(self.runner.run(Path(project)))

    def _stop_ai_run_app(self) -> None:
        if self._ai_run_active and not self._ai_run_reported:
            self._report_ai_run(False, "Đã dừng chạy thử theo yêu cầu.")
        self.runner.stop_vxpemu()

    def _ai_run_output_path(self) -> Path:
        stamp = QDateTime.currentDateTime().toString("yyyyMMdd-HHmmss")
        base = Path(self.session.root) if self.session.root else Path(self.engine_root)
        return base / "build" / "smoke" / f"run-{stamp}.png"

    def _ai_capture_and_report(self) -> None:
        if not self._ai_run_active or self._ai_run_reported:
            return
        window = self._vxp_emu_window
        if window is None or not window.running:
            self._report_ai_run(False, "Giả lập không hiển thị để chụp ảnh kiểm tra.")
            return
        output = self._ai_run_output_path()
        if window.capture_to_file(output):
            self._report_ai_run(
                True,
                "Đã build và chạy game/app trên VXPEmu; đã chụp ảnh kiểm tra.",
                str(output),
            )
            return
        self._ai_run_attempts += 1
        if self._ai_run_attempts >= 8:
            self._report_ai_run(
                True,
                "Game/app đã khởi chạy trên VXPEmu nhưng chưa chụp được ảnh "
                "(khung hình chưa sẵn sàng).",
                "",
            )
            return
        QTimer.singleShot(500, self._ai_capture_and_report)

    def _report_ai_run(self, success: bool, message: str, screenshot: str = "") -> None:
        if self._ai_run_reported:
            return
        self._ai_run_active = False
        self._ai_run_started = False
        self._ai_run_reported = True
        self.ai_chat.on_run_app_finished(bool(success), str(message), str(screenshot or ""))
        if success:
            # Chạy ngầm: đóng giả lập ngay sau khi đã có bằng chứng ảnh chụp.
            self.runner.stop_vxpemu()

    def _open_editor_text_overrides(self) -> dict[Path, str]:
        values: dict[Path, str] = {}
        for group in self.tabs.groups:
            for index in range(group.count()):
                editor = group.editor_at(index)
                if editor and editor.path:
                    try:
                        values[editor.path.resolve()] = editor.toPlainText()
                    except OSError:
                        continue
        return values

    def _prepare_ai_changes(self, payload: object) -> None:
        if not self.session.root:
            self.ai_chat.on_code_changes_failed("Open a project before applying AI code changes.")
            return
        data = payload if isinstance(payload, dict) else {"edits": payload}
        edits = data.get("edits") or []
        try:
            change_set = self.ai_change_service.prepare(
                self.session.root,
                edits,
                text_overrides=self._open_editor_text_overrides(),
            )
        except Exception as exc:
            self._ai_change_set = None
            self.ai_chat.on_code_changes_failed(str(exc))
            return
        self._ai_change_set = change_set
        self.ai_chat.on_code_changes_prepared(change_set.summary())
        self._show_ai_diff(change_set, activate=not bool(data.get("auto_apply")))
        if bool(data.get("auto_apply")):
            QTimer.singleShot(0, self._apply_ai_changes)

    def _show_ai_diff(
        self,
        change_set: PreparedChangeSet | None = None,
        *,
        activate: bool = True,
    ) -> AIDiffView | None:
        if change_set is None:
            change_set = self._ai_change_set
        if change_set is None:
            return None

        def factory():
            view = AIDiffView()
            view.apply_all_requested.connect(self._apply_ai_changes)
            view.reject_all_requested.connect(self._reject_ai_changes)
            view.accept_current_requested.connect(self._accept_ai_change_file)
            view.reject_current_requested.connect(self._reject_ai_change_file)
            return view

        self._enter_editor()
        view = self.tabs.open_tool_tab(
            "ai-diff", "AI Changes", factory, icon("fa5s.code-branch"), activate=activate
        )
        if isinstance(view, AIDiffView):
            view.set_change_set(change_set)
            return view
        return None

    def _review_ai_changes(self) -> None:
        if not self._ai_change_set:
            if self._ai_last_applied is not None:
                view = self._show_ai_diff(self._ai_last_applied, activate=True)
                if view is not None:
                    view.mark_applied(self._ai_last_applied_backup)
                return
            self.show_status("No pending AI code changes")
            return
        self._show_ai_diff(self._ai_change_set, activate=True)

    def _reload_applied_editors(self, change_set: PreparedChangeSet) -> None:
        touched_design = False
        for change in change_set.changes:
            target = change.absolute_path.resolve()
            rel = str(change.relative_path or "").replace("\\", "/").lower()
            if rel.endswith("ui_design.json") or rel.startswith("assets/"):
                touched_design = True
            for group in self.tabs.groups:
                found = group.find_editor(target)
                if not found:
                    continue
                _index, editor = found
                editor.setPlainText(change.after)
                editor.document().setModified(False)
        if self.session.root:
            self.index.set_root(self.session.root)
            self.explorer.tree.refresh()
        if touched_design:
            # AI vừa ghi thiết kế/asset — designer là widget sống nên canvas +
            # registry cũ sẽ giữ nguyên placeholder. Quét lại assets/ rồi nạp lại
            # màn hình từ đĩa (bỏ qua khi người dùng còn bản vẽ chưa lưu).
            designer = self.assets_studio.designer
            designer.sync_project_assets()
            designer.reload_current_screen()

    def _open_ai_touched_tabs(self, change_set: PreparedChangeSet) -> None:
        """Open every AI-touched source file as a VS Code-like editor tab.

        Existing tabs are reused; new/closed files open in the background, each
        receives an AI Modified / AI Created badge, and the first changed file is
        activated after the batch is prepared.
        """
        self._enter_editor()
        opened_targets: list[Path] = []
        for change in change_set.changes:
            target = change.absolute_path.resolve()
            if not target.is_file():
                continue
            editor = self.tabs.open_file(target, activate=False)
            if editor is None:
                continue
            editor.setPlainText(change.after)
            editor.document().setModified(False)
            self.tabs.set_ai_file_status(
                target,
                "modified" if change.existed else "created",
            )
            opened_targets.append(target)

        if opened_targets:
            editor = self.tabs.open_file(opened_targets[0], activate=True)
            if editor is not None:
                editor.setFocus()

    def _apply_ai_changes(self) -> None:
        change_set = self._ai_change_set
        if not change_set:
            self.show_status("No pending AI code changes")
            return
        try:
            applied, backup = self.ai_change_service.apply(change_set)
        except Exception as exc:
            self.ai_chat.on_code_changes_failed(str(exc))
            self.show_status(f"AI code apply failed: {exc}")
            return
        self._reload_applied_editors(change_set)
        self._open_ai_touched_tabs(change_set)
        paths = [path.relative_to(change_set.project_root).as_posix() for path in applied]
        files = [
            {"path": c.relative_path, "added": c.added_lines, "removed": c.removed_lines}
            for c in change_set.changes
        ]
        diffs = {c.relative_path: c.unified_diff() for c in change_set.changes}
        view = self.tabs.tool_widget("ai-diff")
        if isinstance(view, AIDiffView):
            view.mark_applied(backup)
        self._ai_last_applied = change_set
        self._ai_last_applied_backup = backup
        self.ai_chat.on_code_changes_applied(paths, str(backup or ""), files=files, diffs=diffs)
        self.bottom.console.append(
            f"[AI] Applied {len(paths)} code file(s)" + (f"; backup: {backup}" if backup else "")
        )
        self._ai_change_set = None
        self.show_status(f"AI code applied: {len(paths)} file(s)")
        # Antigravity-style: sau khi áp, chờ diagnostic của tệp vừa đổi ổn định
        # rồi bật thẻ "lỗi cần sửa" và mở đúng tệp đầu tiên còn lỗi.
        QTimer.singleShot(700, lambda: self.ai_chat.report_errors_after_change())

    def _reject_ai_changes(self) -> None:
        if not self._ai_change_set:
            return
        self.ai_change_service.reject()
        self._ai_change_set = None
        view = self.tabs.tool_widget("ai-diff")
        if isinstance(view, AIDiffView):
            view.mark_rejected()
        self.ai_chat.on_code_changes_rejected()
        self.show_status("AI code changes rejected")

    def _accept_ai_change_file(self) -> None:
        """Accept file dang chon kieu Codex: ghi ngay + tiep tuc duyet file khac."""
        from app.services.ai_change_service import PreparedChange, PreparedChangeSet

        change_set = self._ai_change_set
        view = self.tabs.tool_widget("ai-diff")
        if not change_set or not isinstance(view, AIDiffView):
            return
        row = view.files.currentRow()
        if not (0 <= row < len(change_set.changes)):
            self.show_status("No AI change file selected")
            return
        rel = change_set.changes[row].relative_path
        try:
            target, backup = self.ai_change_service.apply_one(change_set, row)
        except Exception as exc:
            self.ai_chat.on_code_changes_failed(str(exc))
            self.show_status(f"AI code apply failed: {exc}")
            return
        try:
            text = Path(target).read_text(encoding="utf-8-sig")
        except OSError:
            text = ""
        single = PreparedChangeSet(
            change_set.project_root,
            [PreparedChange(
                relative_path=rel, absolute_path=Path(target),
                before=text, after=text)],
        )
        self._reload_applied_editors(single)
        self._open_ai_touched_tabs(single)
        view.set_change_set(change_set if change_set.changes else None)
        if not change_set.changes:
            view.mark_applied(backup)
            self._ai_last_applied = change_set
            self._ai_last_applied_backup = backup
        self.ai_chat.on_code_changes_applied(
            [rel], str(backup or ""),
            files=[{"path": rel, "added": 0, "removed": 0}])
        self.bottom.console.append(f"[AI] Accepted {rel}" + (f"; backup: {backup}" if backup else ""))
        self.show_status(f"AI code accepted: {rel}")
        QTimer.singleShot(700, lambda: self.ai_chat.report_errors_after_change())

    def _reject_ai_change_file(self) -> None:
        """Reject file dang chon: bo khoi set, giu cac file khac."""
        change_set = self._ai_change_set
        view = self.tabs.tool_widget("ai-diff")
        if not change_set or not isinstance(view, AIDiffView):
            return
        row = view.files.currentRow()
        if not (0 <= row < len(change_set.changes)):
            self.show_status("No AI change file selected")
            return
        try:
            dropped = self.ai_change_service.discard(change_set, row)
        except Exception as exc:
            self.show_status(f"AI code reject failed: {exc}")
            return
        view.set_change_set(change_set if change_set.changes else None)
        if not change_set.changes:
            view.mark_rejected()
            self._ai_change_set = None
            self.ai_chat.on_code_changes_rejected()
        self.show_status(f"AI code rejected: {dropped.relative_path} ({len(change_set.changes)} left)")

    def _ask_ai_about_problems(self, question: str) -> None:
        if not str(question or "").strip():
            return
        self.show_status("Problem sent to Chat AI — press Enter to ask")
        self._set_ai_visible(True)
        self.ai_chat.prefill_question(question)

    def _ai_problems_snapshot(self, *, op: str = "list") -> str:
        """Nền đọc của tool problems: xuất bảng PROBLEMS hiện tại cho AI agent."""
        from app.widgets.bottom_panel import ProblemsView

        view = self.bottom.problems
        rows = view._rows()
        if op == "count":
            return f"PROBLEMS: {len(rows)} mục."
        if not rows:
            return ""
        root = self.session.root
        lines = [
            f"PROBLEMS ({len(rows)} mục, hiển thị tối đa {view.MAX_ITEMS}; "
            "đường dẫn tương đối dự án):"
        ]
        limit = min(len(rows), view.MAX_ITEMS)
        for severity, path, line, column, message in rows[:limit]:
            try:
                shown = Path(path).relative_to(root).as_posix() if root else Path(path).name
            except ValueError:
                shown = Path(path).as_posix()
            col = f":{column}" if column else ""
            lines.append(f"- [{severity.upper()}] {shown}:{line}{col} — {message}")
            snippet = ProblemsView._snippet(path, line)
            if snippet:
                lines.append("  " + snippet.replace("\n", "\n  "))
        if len(rows) > limit:
            lines.append(f"... còn {len(rows) - limit} mục nữa trong bảng PROBLEMS.")
        return "\n".join(lines)

    # ========================================================== layout panes
    def _toggle_left_column(self) -> None:
        visible = not self.project_panel_frame.isVisible()
        self.project_panel_frame.setVisible(visible)
        self.explorer_toggle_button.setChecked(visible)
        self._update_activity_bar()

    def _toggle_console_panel(self) -> None:
        self._set_console_visible(not self._console_visible)

    def _set_console_visible(self, visible: bool) -> None:
        self._console_visible = bool(visible)
        total = max(1, sum(self.center_workspace_column.sizes()))
        if self._console_visible:
            self.bottom.show()
            restored = max(130, min(self._console_last_height, int(total * 0.48)))
            self.center_workspace_column.setSizes([max(180, total - restored), restored])
        else:
            sizes = self.center_workspace_column.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._console_last_height = max(130, sizes[1])
            self.bottom.hide()
            self.center_workspace_column.setSizes([max(1, sum(sizes)), 0])
        self.console_toggle_action.blockSignals(True)
        self.console_toggle_action.setChecked(self._console_visible)
        self.console_toggle_action.blockSignals(False)
        self.bottom_panel_button.setProperty("panelVisible", self._console_visible)
        self.bottom_panel_button.style().unpolish(self.bottom_panel_button)
        self.bottom_panel_button.style().polish(self.bottom_panel_button)
        if (
            self._console_visible
            and self.bottom.currentWidget() is self.bottom.terminal
        ):
            self.bottom.terminal.ensure_started()
        self._update_activity_bar()
        self._schedule_workspace_save()

    def _set_console_action_visible(self, _visible: bool) -> None:
        self.console_toggle_action.blockSignals(True)
        self.console_toggle_action.setChecked(self._console_visible)
        self.console_toggle_action.blockSignals(False)

    def _show_terminal_panel(self) -> None:
        self.bottom.show_terminal()
        self._set_console_visible(True)

    def _show_run_session(self) -> None:
        if self.run_session_dialog is None:
            return
        self.run_session_dialog.show()
        self.run_session_dialog.raise_()
        self.run_session_dialog.activateWindow()

    def show_status(self, message: str) -> None:
        self.engine_state_label.setText(message)
        QTimer.singleShot(2400, self._restore_ready)

    def _restore_ready(self) -> None:
        if not self.runner.is_running and not self.engine_state_label.text().startswith("VXPEmu"):
            self.engine_state_label.setText("VXP Ready")

    def _open_docs(self) -> None:
        for path in (self.engine_root / "doc" / "INDEX.md", self.engine_root / "README.md"):
            if path.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
                return
        NoticeDialog("Tài liệu", "Không tìm thấy tệp tài liệu.", self).exec()

    def show_about(self, tab: str = "about") -> None:
        AboutDialog(self.engine_root, self, start_tab=tab).exec()

    # ========================================================= responsive chrome
    def _apply_responsive_layout(self, width: int) -> None:
        compact = width < 1180
        very_compact = width < 1000
        self.title_bar.set_compact_mode(very_compact)
        self.home_page.set_compact_mode(width < 980)
        for button in (self.run_button, self.stop_button, self.check_button, self.build_button, self.designer_button):
            text = str(button.property("responsiveText") or "")
            button.setText("" if compact else text)
            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonIconOnly
                if compact
                else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            button.setMinimumWidth(31 if compact else 0)
        for index, widget in enumerate(self._status_optional_widgets):
            widget.setVisible(not very_compact or index >= 2)
        task = getattr(self, "task_progress", None)
        if task is not None and not task._drag_active:
            task.snap_to_default()

    # =============================================================== Qt events
    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            controller = getattr(self, "window_state_controller", None)
            if controller is not None:
                controller.handle_window_state_change()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        controller = getattr(self, "window_state_controller", None)
        if controller is not None:
            controller.handle_geometry_change()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        controller = getattr(self, "window_state_controller", None)
        if controller is not None:
            controller.handle_geometry_change()
        self._apply_responsive_layout(event.size().width())
        toast = getattr(self, "app_toast", None)
        if toast is not None and toast.isVisible():
            toast.move(max(12, self.root_frame.width() - toast.width() - 24), 48)

    def _edge_at(self, position: QPoint) -> str | None:
        if self.isMaximized():
            return None
        rect = self.rect()
        margin = RESIZE_MARGIN
        left = position.x() <= margin
        right = position.x() >= rect.width() - margin
        top = position.y() <= margin
        bottom = position.y() >= rect.height() - margin
        if top and left: return "top_left"
        if top and right: return "top_right"
        if bottom and left: return "bottom_left"
        if bottom and right: return "bottom_right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    _CURSORS = {
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._edge_at(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_start_geo = self.geometry()
                self._drag_start_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resizing and self._resize_edge:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            geometry = self._drag_start_geo
            x, y, width, height = (
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
            edge = self._resize_edge
            min_width, min_height = self.minimumWidth(), self.minimumHeight()
            if "left" in edge:
                new_width = max(min_width, width - delta.x())
                x += width - new_width
                width = new_width
            if "right" in edge:
                width = max(min_width, width + delta.x())
            if "top" in edge:
                new_height = max(min_height, height - delta.y())
                y += height - new_height
                height = new_height
            if "bottom" in edge:
                height = max(min_height, height + delta.y())
            self.setGeometry(x, y, width, height)
            event.accept()
            return

        edge = self._edge_at(event.position().toPoint())
        self.setCursor(QCursor(self._CURSORS.get(edge, Qt.CursorShape.ArrowCursor)))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._resizing = False
        self._resize_edge = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self._closing:
            event.accept()
            return
        if self.build_service.active:
            answer = ConfirmDialog.ask(
                "Build in progress",
                "A build is still running. Cancel it and exit?",
                self,
                confirm_text="Yes",
                danger=True,
            )
            if not answer:
                event.ignore()
                return
            self.build_service.cancel()
        designer = self.assets_studio.designer
        if isinstance(designer, UIDesignerView):
            try:
                if designer.has_unsaved_changes():
                    designer.auto_save()
            except Exception:
                pass
        self._save_workspace_session()
        self.window_state_controller.save_persisted_placement()
        if not self.tabs.close_file_tabs():
            event.ignore()
            return
        self._closing = True
        try:
            if self.runner.is_running:
                self.runner.stop()
            self.runner.stop_vxpemu()
            self.vxpemu_panel.shutdown()
            if self._vxp_emu_window is not None:
                self._vxp_emu_window.shutdown()
                self._vxp_emu_window = None
        except Exception as error:
            self.bottom.console.append(f"[Warning] Không thể dừng hoàn toàn tiến trình con: {error}")
        self.ai_chat.shutdown()
        self.bottom.shutdown()
        event.accept()
        super().closeEvent(event)


def QApplication_focus(window):  # noqa: N802 - small focused-widget helper
    from PySide6.QtWidgets import QApplication

    return QApplication.focusWidget()
