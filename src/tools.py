import shutil
from typing import Iterable, List, Tuple
from pathlib import Path

RAW_EXTS = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng", ".rw2", ".orf", ".srw", ".pef", ".raw"}
JPG_EXTS = {".jpg", ".jpeg"}

def list_jpgs(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in JPG_EXTS])