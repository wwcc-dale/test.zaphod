#!/usr/bin/env python3
from pathlib import Path
import json
import frontmatter  # python-frontmatter

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # always “current course”
PAGES_DIR = COURSE_ROOT / "pages" # where applicable


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
            post = frontmatter.load(index_path)
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

    content_dirs = []
    for ext in [".page", ".assignment", ".link", ".file"]:
        content_dirs.extend(PAGES_DIR.rglob(f"*{ext}"))

    for folder in content_dirs:
        process_folder(folder)
        print()  # separate each folder's output with a blank line
