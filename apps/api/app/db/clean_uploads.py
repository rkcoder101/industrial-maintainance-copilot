import shutil
from pathlib import Path

from app.core.config import get_settings


def _is_safe_upload_root(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    unsafe_roots = {Path("/"), Path.home().resolve(), Path("/tmp")}
    return resolved not in unsafe_roots and resolved.name == "uploads" and len(resolved.parts) >= 3


def main() -> None:
    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        raise SystemExit("clean-uploads is only allowed in development or test.")

    upload_root = settings.upload_root_path
    if not _is_safe_upload_root(upload_root):
        raise SystemExit(f"Refusing to clean unsafe upload directory: {upload_root}")

    upload_root.mkdir(parents=True, exist_ok=True, mode=0o750)
    for child in upload_root.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    print(f"Cleaned upload files under {upload_root}")


if __name__ == "__main__":
    main()
