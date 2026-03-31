from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from services.config_service import save_raw_settings


def export_settings_filename() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"inky-planner-settings-{stamp}.json"


def create_settings_backup(settings_path: str | Path, *, reason: str = "backup") -> Path:
    source = Path(settings_path)
    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"settings-{reason}-{stamp}.json"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def import_settings_backup(upload: BinaryIO, settings_path: str | Path) -> Path:
    raw = json.loads(upload.read().decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Imported settings must be a JSON object")
    backup_path = create_settings_backup(settings_path, reason="pre-import")
    save_raw_settings(settings_path, raw)
    return backup_path
