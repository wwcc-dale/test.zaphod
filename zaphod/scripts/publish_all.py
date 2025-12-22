#!/usr/bin/env python3
from pathlib import Path
import os

import markdown2canvas as mc
from markdown2canvas import canvas_objects
from markdown2canvas.setup_functions import make_canvas_api_obj  # [web:131]

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # always “current course”
PAGES_DIR = COURSE_ROOT / "pages" # where applicable


# Optional: disable buggy module handling inside markdown2canvas
def _no_modules(self, course):
    return None


canvas_objects.Page.ensure_in_modules = _no_modules
canvas_objects.Assignment.ensure_in_modules = _no_modules
canvas_objects.Link.ensure_in_modules = _no_modules
canvas_objects.File.ensure_in_modules = _no_modules


def get_changed_files() -> list[Path]:
    """
    Read ZAPHOD_CHANGED_FILES and return them as Path objects.
    Empty list if the env var is missing/empty.
    """
    raw = os.environ.get("ZAPHOD_CHANGED_FILES", "").strip()
    if not raw:
        return []
    return [Path(p) for p in raw.splitlines() if p.strip()]


def iter_all_content_dirs():
    """
    Existing behavior: yield every content folder under pages/
    ending in one of the known extensions.
    """
    for ext in [".page", ".assignment", ".link", ".file"]:
        for folder in PAGES_DIR.rglob(f"*{ext}"):
            yield folder


def iter_changed_content_dirs(changed_files: list[Path]):
    """
    From changed files, yield the content folders that should be
    published by this script.

    Rules:
    - Only care about index.md (or source.md if you want).
    - Must live under pages/**.
    - Parent folder must end with .page / .assignment / .link / .file.
    """
    exts = {".page", ".assignment", ".link", ".file"}
    seen: set[Path] = set()

    for path in changed_files:
        # You can decide to trigger on index.md only, or also on source.md.
        if path.name not in {"index.md", "source.md"}:
            continue

        try:
            rel = path.relative_to(COURSE_ROOT)
        except ValueError:
            continue

        if not rel.parts or rel.parts[0] != "pages":
            continue

        folder = path.parent

        if folder.suffix not in exts:
            continue

        if folder not in seen:
            seen.add(folder)
            yield folder


def make_mc_obj(path: Path):
    s = str(path)
    if s.endswith(".page"):
        return mc.Page(s)
    if s.endswith(".assignment"):
        return mc.Assignment(s)
    if s.endswith(".link"):
        return mc.Link(s)
    if s.endswith(".file"):
        return mc.File(s)
    raise ValueError(f"Unknown type for {s}")


canvas = make_canvas_api_obj()  # uses CANVAS_CREDENTIAL_FILE [web:131]
COURSE_IDS = [1259205]  # your Canvas course ID(s)


if __name__ == "__main__":
    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")

    changed_files = get_changed_files()

    if changed_files:
        # Incremental mode: only publish content dirs related to changed files
        content_dirs = list(iter_changed_content_dirs(changed_files))
        if not content_dirs:
            print("[publish] No relevant changed files; nothing to publish.")
    else:
        # Full mode: no env var => publish everything (existing behavior)
        content_dirs = list(iter_all_content_dirs())

    for course_id in COURSE_IDS:
        course = canvas.get_course(course_id)
        for d in content_dirs:
            try:
                obj = make_mc_obj(d)
                obj.publish(course, overwrite=True)
                print(f"[✓ publish] {d.name}")
            except Exception as e:
                print(f"[publish:err] {d.name}: {e}")
            print()  # blank line between content folders
