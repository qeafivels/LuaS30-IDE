from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import QDir, QPoint, QSortFilterProxyModel, Signal, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QFileSystemModel, QMenu, QTreeView, QWidget,
    QApplication,
)

from app.vxpui.custom_dialog import (
    ConfirmDialog, NoticeDialog, TextInputDialog,
)


class ProjectTreeFilter(QSortFilterProxyModel):
    """VS Code-like tree filter: hides generated/noise folders by default."""
    HIDDEN_NAMES = {".git", ".venv", "__pycache__", ".idea", ".pytest_cache"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_generated = False
        self.generated_names = {"build", "release", "dist"}

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        idx = model.index(row, 0, parent)
        name = model.fileName(idx)
        if name in self.HIDDEN_NAMES:
            return False
        if not self.show_generated and name in self.generated_names:
            return False
        return True

    def lessThan(self, left, right):
        model = self.sourceModel()
        lp = Path(model.filePath(left))
        rp = Path(model.filePath(right))
        if lp.is_dir() != rp.is_dir():
            return lp.is_dir()
        return model.fileName(left).lower() < model.fileName(right).lower()


class ProjectTree(QTreeView):
    file_activated = Signal(object)
    path_changed = Signal(object)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.fs_model = QFileSystemModel(self)
        self.fs_model.setReadOnly(False)
        self.fs_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)

        self.proxy = ProjectTreeFilter(self)
        self.proxy.setSourceModel(self.fs_model)
        self.proxy.setDynamicSortFilter(True)

        self.setModel(self.proxy)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setIndentation(14)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        for column in range(1, 4):
            self.hideColumn(column)

        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setExpandsOnDoubleClick(True)
        self.doubleClicked.connect(self._activate_index)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

        self.project_root: Path | None = None

    def set_project_root(self, root: str | Path) -> None:
        path = Path(root).resolve()
        self.project_root = path
        src_root = self.fs_model.setRootPath(str(path))
        root_index = self.proxy.mapFromSource(src_root)
        self.setRootIndex(root_index)
        self.expand(root_index)
        self.status_message.emit(f"Explorer root: {path}")


    def clear_project_root(self) -> None:
        self.project_root = None
        src_root = self.fs_model.setRootPath("")
        self.setRootIndex(self.proxy.mapFromSource(src_root))
        self.clearSelection()
        self.status_message.emit("Explorer: no project")

    def reveal_path(self, path: str | Path) -> bool:
        """Chọn và cuộn tới `path`; trả về False nếu nó ngoài cây hiện tại.

        Dùng khi lớp ngoài (Project Hub) muốn chỉ ra một thư mục cụ thể mà
        không phải tự đụng vào proxy/QFileSystemModel.
        """
        if self.project_root is None:
            return False
        target = Path(path).resolve()
        try:
            target.relative_to(self.project_root)
        except ValueError:
            return False
        source = self.fs_model.index(str(target))
        if not source.isValid():
            return False
        index = self.proxy.mapFromSource(source)
        if not index.isValid():
            # Bị bộ lọc ẩn (build/.git/...) — không phải lỗi, chỉ là không hiện.
            return False
        self.setCurrentIndex(index)
        self.scrollTo(index)
        return True

    def refresh(self) -> None:
        self.proxy.invalidateFilter()
        self.viewport().update()

    def toggle_generated(self) -> bool:
        self.proxy.show_generated = not self.proxy.show_generated
        self.proxy.invalidateFilter()
        return self.proxy.show_generated

    def expand_all_folders(self) -> None:
        self.expandAll()

    def collapse_all_folders(self) -> None:
        self.collapseAll()
        if self.rootIndex().isValid():
            self.expand(self.rootIndex())

    def selected_path(self) -> Path | None:
        indexes = self.selectedIndexes()
        if not indexes:
            return None
        src = self.proxy.mapToSource(indexes[0])
        return Path(self.fs_model.filePath(src))

    def _path_for_proxy_index(self, index) -> Path:
        src = self.proxy.mapToSource(index)
        return Path(self.fs_model.filePath(src))

    def _activate_index(self, index) -> None:
        path = self._path_for_proxy_index(index)
        if path.is_file():
            self.file_activated.emit(path)

    def _context_menu(self, point: QPoint) -> None:
        selected = self.selected_path()
        base = selected if selected and selected.is_dir() else (selected.parent if selected else self.project_root)
        menu = QMenu(self)

        if selected and selected.is_file():
            open_action = menu.addAction("Open")
            open_action.triggered.connect(lambda: self.file_activated.emit(selected))
            menu.addSeparator()

        if base:
            new_file_action = menu.addAction("New File")
            new_folder_action = menu.addAction("New Folder")
            new_file_action.triggered.connect(lambda: self._new_file(base))
            new_folder_action.triggered.connect(lambda: self._new_folder(base))

        if selected:
            menu.addSeparator()
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")
            rename_action.triggered.connect(lambda: self._rename(selected))
            delete_action.triggered.connect(lambda: self._delete(selected))

            menu.addSeparator()
            copy_path = menu.addAction("Copy Path")
            copy_relative = menu.addAction("Copy Relative Path")
            reveal = menu.addAction("Reveal in File Explorer")
            copy_path.triggered.connect(lambda: QApplication.clipboard().setText(str(selected)))
            copy_relative.triggered.connect(lambda: QApplication.clipboard().setText(self._relative(selected)))
            reveal.triggered.connect(lambda: self._reveal(selected))

        menu.addSeparator()
        expand_action = menu.addAction("Expand All")
        collapse_action = menu.addAction("Collapse All")
        refresh_action = menu.addAction("Refresh")
        show_generated = menu.addAction("Show Generated Folders")
        show_generated.setCheckable(True)
        show_generated.setChecked(self.proxy.show_generated)

        expand_action.triggered.connect(self.expand_all_folders)
        collapse_action.triggered.connect(self.collapse_all_folders)
        refresh_action.triggered.connect(self.refresh)
        show_generated.triggered.connect(lambda: self.toggle_generated())
        menu.exec(self.viewport().mapToGlobal(point))

    def _relative(self, path: Path) -> str:
        if not self.project_root:
            return str(path)
        try:
            return path.relative_to(self.project_root).as_posix()
        except ValueError:
            return str(path)

    def _reveal(self, path: Path) -> None:
        target = path.parent if path.is_file() else path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _new_file(self, directory: Path) -> None:
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if not ok or not name.strip():
            return
        path = directory / name.strip()
        if path.exists():
            QMessageBox.warning(self, "New File", "A file or folder with that name already exists.")
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            self.refresh()
            self.path_changed.emit(path)
            self.file_activated.emit(path)
        except OSError as exc:
            QMessageBox.critical(self, "New File", str(exc))

    def _new_folder(self, directory: Path) -> None:
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        path = directory / name.strip()
        try:
            path.mkdir(parents=False)
            self.refresh()
            self.path_changed.emit(path)
        except OSError as exc:
            QMessageBox.critical(self, "New Folder", str(exc))

    def _rename(self, path: Path) -> None:
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=path.name)
        if not ok or not name.strip() or name.strip() == path.name:
            return
        dst = path.with_name(name.strip())
        if dst.exists():
            QMessageBox.warning(self, "Rename", "A file or folder with that name already exists.")
            return
        try:
            path.rename(dst)
            self.refresh()
            self.path_changed.emit(dst)
        except OSError as exc:
            QMessageBox.critical(self, "Rename", str(exc))

    def _delete(self, path: Path) -> None:
        answer = QMessageBox.question(
            self, "Delete", f"Delete {path.name}?\\n\\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            self.refresh()
            self.path_changed.emit(path)
        except OSError as exc:
            QMessageBox.critical(self, "Delete", str(exc))
