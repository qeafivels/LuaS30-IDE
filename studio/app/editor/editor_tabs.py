from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QLabel, QMenu, QTabBar, QTabWidget, QToolButton, QWidget,
)

from app.ui import palette
from app.ui.icons import apply_icon
from app.vxpui.custom_dialog import CustomDialog, NoticeDialog
from app.vxpui.icons import icon as chrome_icon

from .code_editor import CodeEditor
from .editor_pane import EditorPane

# Mã result riêng cho nút "Không lưu" trong hộp thoại Unsaved changes.
_DISCARD = -100


TEXT_EXTENSIONS = {
    ".lua", ".txt", ".md", ".json", ".ini", ".cfg", ".csv", ".xml", ".html", ".css",
    ".js", ".py", ".c", ".h", ".cpp", ".hpp", ".bat", ".ps1",
}

CLOSE_GLYPH_SIZE = 11

# Icon nhỏ trên tab soạn thảo theo loại tệp (kiểu VS Code trong ảnh mẫu).
_CODE_SUFFIXES = {".lua", ".py", ".js", ".c", ".h", ".cpp", ".hpp", ".css", ".html", ".ps1", ".bat"}
_DATA_SUFFIXES = {".json", ".ini", ".cfg", ".csv", ".xml"}


def file_tab_icon(path: Path) -> QIcon:
    suffix = path.suffix.lower()
    if suffix in _CODE_SUFFIXES:
        return chrome_icon("fa5s.file-code", palette.AMBER)
    if suffix in _DATA_SUFFIXES:
        return chrome_icon("fa5s.file-alt", palette.ACCENT_LIGHT)
    return chrome_icon("fa5s.file", palette.TEXT_3)


class _TabCloseButton(QToolButton):
    """Nút đóng tab của Studio.

    Qt vẽ nút đóng bằng pixmap CHUẨN `QStyle::SP_TabCloseButton` — dưới dạng
    một ô X ĐỎ, giống nhau ở mọi style và cả khi không có stylesheet. Đó không
    phải lỗi theme, nhưng nó lệch hẳn tông xám/cam của Studio. Gắn icon vào nút
    Qt tự tạo KHÔNG ăn: stylesheet style bỏ qua icon của subcontrol
    `QTabBar::close-button`. Cách duy nhất có tác dụng là tự sở hữu nút.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("TabCloseButton")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_icon(self, "close", CLOSE_GLYPH_SIZE, palette.TEXT_4)


class _AITabStatusBadge(QLabel):
    """Badge nhỏ trên tab nguồn cho biết tệp vừa được AI sửa hay tạo mới."""

    LABELS = {
        "modified": "AI Modified",
        "created": "AI Created",
    }

    def __init__(self, state: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AITabStatusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMargin(0)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        value = str(state or "").strip().lower()
        if value not in self.LABELS:
            raise ValueError(f"Unsupported AI tab state: {state}")
        self.setProperty("aiState", value)
        label = self.LABELS[value]
        self.setText(label)
        self.setToolTip(label)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class StudioTabBar(QTabBar):
    """QTabBar dùng nút đóng riêng của Studio thay pixmap đỏ mặc định của Qt."""

    close_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._installing = False

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._install_close_button(index)

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        # setTabButton() kéo theo tabLayoutChange() -> phải chặn tái nhập
        if self._installing:
            return
        for index in range(self.count()):
            self._install_close_button(index)

    def _install_close_button(self, index: int) -> None:
        existing = self.tabButton(index, QTabBar.ButtonPosition.RightSide)
        if existing is None or isinstance(existing, _TabCloseButton):
            return
        self._installing = True
        try:
            button = _TabCloseButton(self)
            button.clicked.connect(lambda _=False, b=button: self._request_close(b))
            self.setTabButton(index, QTabBar.ButtonPosition.RightSide, button)
        finally:
            self._installing = False

    def _request_close(self, button: _TabCloseButton) -> None:
        # tra chỉ số LÚC BẤM: tab có thể đã bị kéo đổi chỗ kể từ lúc tạo nút
        for index in range(self.count()):
            if self.tabButton(index, QTabBar.ButtonPosition.RightSide) is button:
                self.close_requested.emit(index)
                return


class EditorTabs(QTabWidget):
    cursor_info_changed = Signal(int, int, int)
    file_opened = Signal(object)
    file_saved = Signal(object)
    current_editor_changed = Signal(object)
    diagnostics_changed = Signal(object, object)
    go_to_definition_requested = Signal(str, object)
    request_find = Signal(bool)
    state_changed = Signal()
    close_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorTabs")
        self.setTabBar(StudioTabBar(self))
        self.setTabsClosable(True)
        self.tabBar().close_requested.connect(self.close_tab)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabBar().setUsesScrollButtons(True)
        self.tabBar().setExpanding(False)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._sync_current)
        self.tabBar().tabMoved.connect(lambda *_: self.state_changed.emit())
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)
        self._tool_tabs: dict[str, QWidget] = {}


    def _show_tab_context_menu(self, pos: QPoint) -> None:
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return
        menu = QMenu(self)
        close_action = menu.addAction("Close")
        close_others_action = menu.addAction("Close Others")
        menu.addSeparator()
        close_all_action = menu.addAction("Close All Tabs")
        chosen = menu.exec(self.tabBar().mapToGlobal(pos))
        if chosen is close_action:
            self.close_tab(index)
        elif chosen is close_others_action:
            self.close_others(index)
        elif chosen is close_all_action:
            self.close_all_requested.emit()

    def close_others(self, keep_index: int) -> bool:
        keep = self.widget(keep_index)
        for index in range(self.count()-1, -1, -1):
            if self.widget(index) is keep:
                continue
            if not self.close_tab(index):
                return False
        if keep is not None:
            current = self.indexOf(keep)
            if current >= 0:
                self.setCurrentIndex(current)
        return True


    def open_tool_tab(
        self,
        key: str,
        title: str,
        widget_factory,
        icon: QIcon | None = None,
        *,
        insert_at: int | None = None,
        activate: bool = True,
    ) -> QWidget:
        existing = self._tool_tabs.get(key)
        if existing is not None:
            index = self.indexOf(existing)
            if index >= 0:
                if insert_at is not None:
                    target = max(0, min(int(insert_at), self.count() - 1))
                    if index != target:
                        self.tabBar().moveTab(index, target)
                        index = target
                if activate:
                    self.setCurrentIndex(index)
                return existing
            self._tool_tabs.pop(key, None)

        widget = widget_factory()
        widget.setProperty("luas30ToolKey", key)
        if insert_at is None:
            index = self.addTab(widget, icon or QIcon(), title)
        else:
            index = self.insertTab(
                max(0, min(int(insert_at), self.count())),
                widget,
                icon or QIcon(),
                title,
            )
        self.setTabToolTip(index, title)
        self._tool_tabs[key] = widget
        if activate:
            self.setCurrentIndex(index)
        self.state_changed.emit()
        return widget

    def tool_widget(self, key: str) -> QWidget | None:
        widget = self._tool_tabs.get(key)
        if widget is not None and self.indexOf(widget) >= 0:
            return widget
        self._tool_tabs.pop(key, None)
        return None

    def focus_tool_tab(self, key: str) -> bool:
        widget = self.tool_widget(key)
        if widget is None:
            return False
        self.setCurrentWidget(widget)
        return True

    def current_tool_key(self) -> str | None:
        widget = self.currentWidget()
        if widget is None:
            return None
        value = widget.property("luas30ToolKey")
        return str(value) if value else None

    def _pane(self, index: int) -> EditorPane | None:
        widget = self.widget(index)
        return widget if isinstance(widget, EditorPane) else None

    def current_editor(self) -> CodeEditor | None:
        pane = self._pane(self.currentIndex())
        return pane.editor if pane else None

    def editor_at(self, index: int) -> CodeEditor | None:
        pane = self._pane(index)
        return pane.editor if pane else None

    def find_editor(self, path: Path) -> tuple[int, CodeEditor] | None:
        resolved = path.resolve()
        for i in range(self.count()):
            editor = self.editor_at(i)
            if editor and editor.path and editor.path.resolve() == resolved:
                return i, editor
        return None

    def set_ai_file_status(self, path: str | Path, state: str) -> bool:
        """Show an AI Created / AI Modified badge on an already-open file tab."""
        resolved = Path(path).resolve()
        found = self.find_editor(resolved)
        if not found:
            return False
        index, _editor = found
        value = str(state or "").strip().lower()
        if value not in _AITabStatusBadge.LABELS:
            raise ValueError(f"Unsupported AI tab state: {state}")

        bar = self.tabBar()
        badge = bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
        if not isinstance(badge, _AITabStatusBadge):
            badge = _AITabStatusBadge(value, bar)
            bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, badge)
        else:
            badge.set_state(value)

        label = _AITabStatusBadge.LABELS[value]
        self.setTabToolTip(index, f"{resolved}\n{label}")
        self.state_changed.emit()
        return True

    def clear_ai_file_status(self, path: str | Path) -> bool:
        """Remove the transient AI badge while keeping the file tab open."""
        resolved = Path(path).resolve()
        found = self.find_editor(resolved)
        if not found:
            return False
        index, _editor = found
        bar = self.tabBar()
        badge = bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
        if isinstance(badge, _AITabStatusBadge):
            bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, None)
            badge.deleteLater()
        self.setTabToolTip(index, str(resolved))
        self.state_changed.emit()
        return True

    def _connect_editor(self, editor: CodeEditor) -> None:
        editor.document().modificationChanged.connect(
            lambda modified, ed=editor: self._update_tab_title(ed, modified)
        )
        editor.cursor_info_changed.connect(self.cursor_info_changed)
        editor.diagnostics_changed.connect(
            lambda items, ed=editor: self.diagnostics_changed.emit(ed.path, items)
        )
        editor.go_to_definition_requested.connect(self.go_to_definition_requested)
        editor.request_find.connect(self.request_find)
        editor.document().contentsChanged.connect(self.state_changed)

    def open_file(self, path: str | Path, *, activate: bool = True) -> CodeEditor | None:
        file_path = Path(path).resolve()
        if not file_path.is_file():
            return None
        existing = self.find_editor(file_path)
        if existing:
            if activate:
                self.setCurrentIndex(existing[0])
            return existing[1]
        if file_path.suffix.lower() not in TEXT_EXTENSIONS and file_path.name not in {"Makefile"}:
            NoticeDialog("LuaS30 Studio", f"Binary preview is not supported yet:\n{file_path}", self).exec()
            return None
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
            except OSError as exc:
                NoticeDialog("Open file failed", str(exc), self, error=True).exec()
                return None
        except OSError as exc:
            NoticeDialog("Open file failed", str(exc), self, error=True).exec()
            return None

        pane = EditorPane(file_path)
        editor = pane.editor
        editor.setPlainText(text)
        editor.document().setModified(False)
        self._connect_editor(editor)
        index = self.addTab(pane, file_tab_icon(file_path), file_path.name)
        self.setTabToolTip(index, str(file_path))
        if activate:
            self.setCurrentIndex(index)
        self.file_opened.emit(file_path)
        self.state_changed.emit()
        return editor

    def new_file(self) -> CodeEditor:
        pane = EditorPane()
        editor = pane.editor
        self._connect_editor(editor)
        index = self.addTab(pane, "Untitled")
        self.setCurrentIndex(index)
        editor.setFocus()
        self.state_changed.emit()
        return editor

    def save_current(self) -> bool:
        editor = self.current_editor()
        if not editor:
            return True
        return self.save_editor(editor)

    def save_editor(self, editor: CodeEditor, force_dialog: bool = False) -> bool:
        path = editor.path
        if force_dialog or path is None:
            initial = str(path.parent if path else Path.home())
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save source file", initial,
                "Lua (*.lua);;Text (*.txt);;All Files (*)",
            )
            if not filename:
                return False
            path = Path(filename).resolve()
            editor.attach_path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(editor.toPlainText(), encoding="utf-8", newline="\n")
        except OSError as exc:
            NoticeDialog("Save file failed", str(exc), self, error=True).exec()
            return False
        editor.document().setModified(False)
        self._update_tab_title(editor, False)
        idx = self._index_of_editor(editor)
        if idx >= 0:
            self.setTabToolTip(idx, str(path))
        self.file_saved.emit(path)
        self.state_changed.emit()
        return True

    def save_current_as(self) -> bool:
        editor = self.current_editor()
        return self.save_editor(editor, True) if editor else True

    def save_all(self) -> bool:
        for i in range(self.count()):
            editor = self.editor_at(i)
            if editor and editor.document().isModified():
                if not self.save_editor(editor):
                    return False
        return True

    def close_tab(self, index: int) -> bool:
        editor = self.editor_at(index)
        if editor and not self._confirm_discard_or_save(editor):
            return False
        widget = self.widget(index)
        if widget is not None:
            key = widget.property("luas30ToolKey")
            if key:
                self._tool_tabs.pop(str(key), None)
        self.removeTab(index)
        if widget:
            widget.deleteLater()
        self.state_changed.emit()
        return True

    def close_file_tabs(self) -> bool:
        for index in range(self.count() - 1, -1, -1):
            if self._pane(index) is not None:
                if not self.close_tab(index):
                    return False
        return True

    def close_all(self) -> bool:
        while self.count():
            if not self.close_tab(0):
                return False
        return True

    def _confirm_discard_or_save(self, editor: CodeEditor) -> bool:
        if not editor.document().isModified():
            return True
        box = CustomDialog("Unsaved changes", parent=self, width=500, height=250)
        from PySide6.QtWidgets import QLabel
        prompt = QLabel(f"Save changes to {editor.display_name}?")
        prompt.setWordWrap(True)
        prompt.setObjectName("NoticeText")
        box.add_body_widget(prompt)
        cancel = box.add_footer_button("Hủy bỏ", ghost=True, icon_name="fa5s.times")
        discard = box.add_footer_button("Không lưu", danger=True, icon_name="fa5s.trash-alt")
        save = box.add_footer_button("Lưu", accent=True, icon_name="fa5s.save")
        cancel.clicked.connect(box.reject)
        discard.clicked.connect(lambda: box.done(_DISCARD))
        save.clicked.connect(box.accept)
        result = box.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.save_editor(editor)
        if result == _DISCARD:
            return True
        return False

    def _index_of_editor(self, editor: CodeEditor) -> int:
        for i in range(self.count()):
            if self.editor_at(i) is editor:
                return i
        return -1

    def _update_tab_title(self, editor: CodeEditor, modified: bool) -> None:
        idx = self._index_of_editor(editor)
        if idx < 0:
            return
        self.setTabText(idx, editor.display_name + (" *" if modified else ""))

    def _sync_current(self, _index: int) -> None:
        editor = self.current_editor()
        self.current_editor_changed.emit(editor)
        if editor:
            cursor = editor.textCursor()
            self.cursor_info_changed.emit(
                cursor.blockNumber() + 1, cursor.positionInBlock() + 1, len(cursor.selectedText())
            )
            self.diagnostics_changed.emit(editor.path, editor.diagnostics)
        else:
            # Tool tabs share the VS Code-like editor strip. Do not erase Problems
            # merely because the active tab is a tool rather than a source editor.
            if not self.current_tool_key():
                self.cursor_info_changed.emit(1, 1, 0)
                self.diagnostics_changed.emit(None, [])
