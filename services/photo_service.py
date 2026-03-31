from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def list_photos(photo_folder: str | Path, project_root: Path) -> list[Path]:
    folder = resolve_photo_folder(photo_folder, project_root, create=False)
    if folder is None or not folder.exists() or not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)


def pick_photo(photo_folder: str | Path, project_root: Path) -> Path | None:
    photos = list_photos(photo_folder, project_root)
    return photos[0] if photos else None


def save_uploaded_photos(files: list, photo_folder: str | Path, project_root: Path) -> list[Path]:
    folder = resolve_photo_folder(photo_folder, project_root, create=True)
    saved: list[Path] = []
    for upload in files:
        if upload is None or not getattr(upload, "filename", ""):
            continue
        filename = secure_filename(upload.filename)
        if not filename:
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            continue
        target = folder / filename
        if target.exists():
            target = folder / f"{Path(filename).stem}-{uuid4().hex[:8]}{suffix}"
        upload.save(target)
        saved.append(target)

    if saved:
        sample_path = folder / "sample_photo.png"
        if sample_path.exists():
            sample_path.unlink()

    return saved


def delete_photo(photo_folder: str | Path, project_root: Path, filename: str) -> bool:
    folder = resolve_photo_folder(photo_folder, project_root, create=False)
    if folder is None:
        return False
    target = folder / Path(filename).name
    if not target.exists() or not target.is_file():
        return False
    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    target.unlink()
    return True


def delete_all_photos(photo_folder: str | Path, project_root: Path) -> int:
    folder = resolve_photo_folder(photo_folder, project_root, create=False)
    if folder is None:
        return 0
    removed = 0
    for target in folder.iterdir():
        if not target.is_file() or target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        target.unlink()
        removed += 1
    return removed


def resolve_photo_folder(photo_folder: str | Path, project_root: Path, *, create: bool) -> Path | None:
    folder = Path(photo_folder)
    candidate = folder if folder.is_absolute() else project_root / folder
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    return candidate if candidate.exists() else None
