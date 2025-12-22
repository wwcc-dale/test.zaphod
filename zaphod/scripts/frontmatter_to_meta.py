#!/usr/bin/env python3
from pathlib import Path
import json
import os

import frontmatter  # python-frontmatter [web:101]

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # always “current course”
PAGES_DIR = COURSE_ROOT / "pages" # where applicable


def get_changed_files() -> list[Path]:
    """
    Read ZAPHOD_CHANGED_FILES and return them as Path objects.
    If the env var is missing/empty, return an empty list.
    """
    raw = os.environ.get("ZAPHOD_CHANGED_FILES", "").strip()
    if not raw:
        return []
    return [Path(p) for p in raw.splitlines() if p.strip()]


def iter_all_content_dirs():
    """
    Existing full-scan behavior: yield every content folder under pages/
    ending in one of the known extensions.
    """
    for ext in [".page", ".assignment", ".link", ".file"]:
        for folder in PAGES_DIR.rglob(f"*{ext}"):
            yield folder


def iter_changed_content_dirs(changed_files: list[Path]):
    """
    From the changed files, yield the content folders that should be
    processed by this script.

    Rules:
    - Only care about index.md files.
    - Only if they live inside pages/** and inside a folder whose
      name ends with one of .page / .assignment / .link / .file.
    """
    exts = {".page", ".assignment", ".link", ".file"}

    seen: set[Path] = set()

    for path in changed_files:
        if path.name != "index.md":
            continue

        try:
            # Only consider files under this COURSE_ROOT
            rel = path.relative_to(COURSE_ROOT)
        except ValueError:
            continue

        # Must be under pages/
        if not rel.parts or rel.parts[0] != "pages":
            continue

        # Folder is the parent of index.md
        folder = path.parent

        if folder.suffix not in exts:
            continue

        if folder not in seen:
            seen.add(folder)
            yield folder


def process_folder(folder: Path):
    index_path = folder / "index.md"
    meta_path = folder / "meta.json"
    source_path = folder / "source.md"

    has_index = index_path.is_file()
    has_meta = meta_path.is_file()
    has_source = source_path.is_file()

    # 1) Preferred: index.md with frontmatter
    if has_index:
        try:
            post = frontmatter.load(index_path)  # [web:98][web:101]
            metadata = dict(post.metadata)
            content = post.content.strip() + "\n"
        except Exception as e:
            print(f"[frontmatter:warn] {folder.name}: {e}")
        else:
            # Require minimum keys for a valid Canvas object
            for k in ["name", "type"]:
                if k not in metadata:
                    print(f"[frontmatter:warn] {folder.name}: missing '{k}', using meta.json if present")
                    break
            else:
                with meta_path.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                with source_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[✓ frontmatter] {folder.name}")
                return

    # 2) Fallback: existing meta.json + source.md
    if has_meta and has_source:
        print(f"[↻ meta.json] {folder.name}")
        return

    # 3) Nothing usable
    print(f"[frontmatter:err] {folder.name}: no usable metadata (index.md or meta.json/source.md)")


if __name__ == "__main__":
    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")

    changed_files = get_changed_files()

    if changed_files:
        # Incremental mode: only process content folders for changed index.md files
        content_dirs = list(iter_changed_content_dirs(changed_files))
        if not content_dirs:
            print("[frontmatter] No relevant changed index.md files; nothing to do.")
    else:
        # Full mode: no env var => process everything (existing behavior)
        content_dirs = list(iter_all_content_dirs())

    for folder in content_dirs:
        process_folder(folder)
        print()  # separate each folder's output with a blank line
