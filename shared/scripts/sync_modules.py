#!/usr/bin/env python3
"""
sync_modules.py (Zaphod)

Ensure Canvas modules contain all items declared in meta.json for:

  - .page        -> Canvas Page module items
  - .assignment  -> Canvas Assignment module items
  - .file        -> Canvas File module items
  - .link        -> Canvas ExternalUrl module items

For each content folder under pages/, this script:

  1. Reads meta.json and looks for:
       - type: "Page", "Assignment", "File", or "Link" (case-insensitive)
       - name: title/name used in Canvas
       - modules: list of module names
       - indent: optional integer indent level
       - (file) filename, title
       - (link) external_url, new_tab
  2. Finds or creates each listed module.
  3. Ensures the corresponding Canvas item is present in that module
     with the appropriate type and indent, creating it if missing.

Assumptions:
  - Run from the course root (where pages/ lives).
  - Env:
      CANVAS_CREDENTIAL_FILE   path to credentials.txt
      COURSE_ID                Canvas course id
  - Credentials file defines:
      API_KEY = "..."
      API_URL = "https://yourcanvas.institution.edu"
"""

from pathlib import Path
import json
import os

from canvasapi import Canvas

SCRIPT_DIR = Path(__file__).resolve().parent
COURSE_ROOT = Path.cwd()
PAGES_DIR = COURSE_ROOT / "pages"


# ---------- Canvas helpers ----------

def get_canvas():
    cred_path = os.environ.get("CANVAS_CREDENTIAL_FILE")
    if not cred_path:
        raise SystemExit("CANVAS_CREDENTIAL_FILE is not set")

    cred_file = Path(cred_path)
    if not cred_file.is_file():
        raise SystemExit(f"CANVAS_CREDENTIAL_FILE does not exist: {cred_file}")

    ns = {}
    exec(cred_file.read_text(encoding="utf-8"), ns)
    try:
        api_key = ns["API_KEY"]
        api_url = ns["API_URL"]
    except KeyError as e:
        raise SystemExit(
            f"Credentials file must define API_KEY and API_URL. Missing {e!r}"
        )
    return Canvas(api_url, api_key)


def load_meta(folder: Path) -> dict:
    meta_path = folder / "meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"No meta.json in folder {folder}")
    with meta_path.open(encoding="utf-8") as f:
        return json.load(f)


def ensure_module(course, name: str):
    """
    Find or create a module with the given name.
    """
    for m in course.get_modules():
        if m.name == name:
            return m
    return course.create_module({"name": name})


def module_has_item(
    module,
    item_type: str,
    *,
    page_url=None,
    content_id=None,
    external_url=None,
) -> bool:
    """
    Check if the module already has an item of the given type pointing at the same content.
    """
    for item in module.get_module_items():
        if item.type != item_type:
            continue

        if item_type == "Page":
            if getattr(item, "page_url", None) == page_url:
                return True
        elif item_type in {"Assignment", "File"}:
            if getattr(item, "content_id", None) == content_id:
                return True
        elif item_type == "ExternalUrl":
            if getattr(item, "external_url", None) == external_url:
                return True

    return False


# ---------- Find Canvas objects by name ----------

def find_page(course, title: str):
    for page in course.get_pages():
        if page.title == title:
            return page
    return None


def find_assignment(course, name: str):
    for a in course.get_assignments():
        if a.name == name:
            return a
    return None


def find_file(course, filename: str):
    """
    Naive search by filename; adjust if you need stricter path matching.
    """
    for f in course.get_files():
        if f.filename == filename:
            return f
    return None


# ---------- Sync functions per content type ----------

def sync_page(course, folder: Path, meta: dict):
    title = meta.get("name")
    modules = meta.get("modules") or []
    indent = meta.get("indent", 0)

    if not title:
        print(f"[modules:warn] {folder.name}: missing 'name' in meta.json for page")
        return
    if not modules:
        return

    page = find_page(course, title)
    if not page:
        print(f"[modules:warn] {folder.name}: page title '{title}' not found in Canvas")
        return

    page_url = page.url
    for mname in modules:
        module = ensure_module(course, mname)
        if module_has_item(module, "Page", page_url=page_url):
            print(f"[modules] {folder.name}: already in module '{mname}' (Page)")
            continue

        module.create_module_item(
            module_item={
                "type": "Page",
                "page_url": page_url,
                "title": title,
                "indent": indent,
            }
        )
        print(f"[modules] {folder.name}: added to module '{mname}' (Page)")


def sync_assignment(course, folder: Path, meta: dict):
    name = meta.get("name")
    modules = meta.get("modules") or []
    indent = meta.get("indent", 0)

    if not name:
        print(f"[modules:warn] {folder.name}: missing 'name' in meta.json for assignment")
        return
    if not modules:
        return

    assignment = find_assignment(course, name)
    if not assignment:
        print(f"[modules:warn] {folder.name}: assignment name '{name}' not found in Canvas")
        return

    content_id = assignment.id
    for mname in modules:
        module = ensure_module(course, mname)
        if module_has_item(module, "Assignment", content_id=content_id):
            print(f"[modules] {folder.name}: already in module '{mname}' (Assignment)")
            continue

        module.create_module_item(
            module_item={
                "type": "Assignment",
                "content_id": content_id,
                "title": name,
                "indent": indent,
            }
        )
        print(f"[modules] {folder.name}: added to module '{mname}' (Assignment)")


def sync_file_item(course, folder: Path, meta: dict):
    filename = meta.get("filename")
    modules = meta.get("modules") or []
    indent = meta.get("indent", 0)
    title = meta.get("title", filename)

    if not filename:
        print(f"[modules:warn] {folder.name}: missing 'filename' in meta.json for file")
        return
    if not modules:
        return

    file_obj = find_file(course, filename)
    if not file_obj:
        print(f"[modules:warn] {folder.name}: file '{filename}' not found in Canvas")
        return

    content_id = file_obj.id
    for mname in modules:
        module = ensure_module(course, mname)
        if module_has_item(module, "File", content_id=content_id):
            print(f"[modules] {folder.name}: already in module '{mname}' (File)")
            continue

        module.create_module_item(
            module_item={
                "type": "File",
                "content_id": content_id,
                "title": title,
                "indent": indent,
            }
        )
        print(f"[modules] {folder.name}: added to module '{mname}' (File)")


def sync_link(course, folder: Path, meta: dict):
    external_url = meta.get("external_url")
    name = meta.get("name")
    modules = meta.get("modules") or []
    indent = meta.get("indent", 0)
    new_tab = bool(meta.get("new_tab", False))

    if not external_url or not name:
        print(f"[modules:warn] {folder.name}: missing 'external_url' or 'name' in meta.json for link")
        return
    if not modules:
        return

    for mname in modules:
        module = ensure_module(course, mname)
        if module_has_item(module, "ExternalUrl", external_url=external_url):
            print(f"[modules] {folder.name}: already in module '{mname}' (ExternalUrl)")
            continue

        module.create_module_item(
            module_item={
                "type": "ExternalUrl",
                "external_url": external_url,
                "title": name,
                "new_tab": new_tab,
                "indent": indent,
            }
        )
        print(f"[modules] {folder.name}: added to module '{mname}' (ExternalUrl)")


# ---------- Main ----------

def main():
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    canvas = get_canvas()
    course = canvas.get_course(int(course_id))

    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")

    print(f"[modules] Syncing modules in course {course.name} (ID {course_id})")

    content_dirs = []
    for ext in (".page", ".assignment", ".file", ".link"):
        content_dirs.extend(PAGES_DIR.rglob(f"*{ext}"))

    if not content_dirs:
        print("[modules] No content folders under pages/")
        return

    for folder in content_dirs:
        try:
            meta = load_meta(folder)
        except FileNotFoundError as e:
            print(f"[modules:warn] {folder.name}: {e}")
            continue

        t = str(meta.get("type", "")).lower()
        if t == "page":
            sync_page(course, folder, meta)
        elif t == "assignment":
            sync_assignment(course, folder, meta)
        elif t == "file":
            sync_file_item(course, folder, meta)
        elif t == "link":
            sync_link(course, folder, meta)
        else:
            print(f"[modules:warn] {folder.name}: unsupported type '{t}' in meta.json")

    print("[modules] Done.")


if __name__ == "__main__":
    main()
