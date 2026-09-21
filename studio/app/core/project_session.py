from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

from app.core.paths import config_dir, ensure_user_dirs, projects_root
from app.core.app_id import rewrite_project_identity

_INVALID_PROJECT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

PROJECT_TEMPLATES = {
    "basic": "basic",
    "doodle-quest": "DoodleQuest",
    "ninja-runner": "NinjaRunner",
    "catbox-mre": "CatBoxMRE",
}

@dataclass(slots=True)
class ProjectInfo:
    root: Path

    @property
    def name(self) -> str:
        return self.root.name

class ProjectSession(QObject):
    project_changed = Signal(object)

    def __init__(self, engine_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.engine_root = engine_root.resolve()
        ensure_user_dirs()
        # v1.4.1 stores settings as an explicit INI under AppData instead of
        # relying on the Windows registry. Migrate lastProject once if available.
        legacy_settings = QSettings()
        self.settings = QSettings(str(config_dir() / "studio.ini"), QSettings.Format.IniFormat)
        if not self.settings.contains("lastProject") and legacy_settings.contains("lastProject"):
            self.settings.setValue("lastProject", legacy_settings.value("lastProject", "", str))
            self.settings.sync()
        self._project: ProjectInfo | None = None

    @property
    def project(self) -> ProjectInfo | None:
        return self._project

    @property
    def root(self) -> Path | None:
        return self._project.root if self._project else None

    @property
    def default_projects_root(self) -> Path:
        root = projects_root()
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def validate_project_name(name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Project name cannot be empty.")
        if cleaned in {".", ".."}:
            raise ValueError("Invalid project name.")
        if _INVALID_PROJECT_CHARS.search(cleaned):
            raise ValueError('Project name cannot contain < > : " / \\ | ? *')
        if cleaned.endswith((" ", ".")):
            raise ValueError("Project name cannot end with a space or dot.")
        if cleaned.upper() in _RESERVED_NAMES:
            raise ValueError(f"'{cleaned}' is reserved by Windows.")
        return cleaned

    def project_path(self, name: str) -> Path:
        return self.default_projects_root / self.validate_project_name(name)

    def create_project(
        self,
        name: str,
        metadata: dict | None = None,
        sdk_metadata: dict | None = None,
        *,
        template_name: str = "basic",
    ) -> ProjectInfo:
        name = self.validate_project_name(name)
        destination = self.project_path(name)
        if destination.exists():
            raise FileExistsError(destination)

        template_key = str(template_name or "basic").strip()
        template_dir = PROJECT_TEMPLATES.get(template_key)
        if not template_dir:
            raise ValueError(f"Unknown project template: {template_key}")

        template = self.engine_root / "templates" / template_dir
        if not template.is_dir():
            raise FileNotFoundError(f"Project template not found: {template}")

        shutil.copytree(template, destination)
        descriptor = destination / "project.json"
        if descriptor.is_file():
            rewrite_project_identity(
                descriptor,
                projects_root=self.default_projects_root,
                name=name,
                assign_new_app_id=True,
            )
            if metadata:
                try:
                    payload = json.loads(descriptor.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError, TypeError):
                    payload = {"name": name}
                appid = payload.get("appid")
                payload.update(dict(metadata))
                payload["name"] = name
                payload["template"] = template_key
                if appid is not None:
                    payload["appid"] = appid
                descriptor.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

        if sdk_metadata:
            sdk_dir = destination / ".luas30"
            sdk_dir.mkdir(parents=True, exist_ok=True)
            (sdk_dir / "mre_sdk.json").write_text(
                json.dumps(dict(sdk_metadata), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        return self.open_project(destination)

    def open_project(self, root: str | Path) -> ProjectInfo:
        path = Path(root).expanduser().resolve()
        if not path.is_dir():
            raise NotADirectoryError(path)
        self._project = ProjectInfo(path)
        self.settings.setValue("lastProject", str(path))
        self.settings.sync()
        self.project_changed.emit(self._project)
        return self._project


    def close_project(self) -> None:
        self._project = None
        self.settings.remove("lastProject")
        self.settings.sync()
        self.project_changed.emit(None)

    def load_initial_project(self) -> ProjectInfo | None:
        last = self.settings.value("lastProject", "", str)
        if last and Path(last).is_dir():
            return self.open_project(last)
        return None
