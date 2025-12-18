#!/usr/bin/env python3
from pathlib import Path
import json
import os
from canvasapi import Canvas

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # always “current course”
PAGES_DIR = COURSE_ROOT / "pages" # where applicable

COURSE_IDS = [1259205]  # your Canvas course ID(s)


def get_canvas():
    cred_path = os.environ.get("CANVAS_CREDENTIAL_FILE")
    if not cred_path:
        raise SystemExit("CANVAS_CREDENTIAL_FILE not set")
    cred_file = Path(cred_path)
    if not cred_file.is_file():
        raise SystemExit(f"CANVAS_CREDENTIAL_FILE does not exist: {cred_file}")

    ns: dict = {}
    exec(cred_file.read_text(encoding="utf-8"), ns)
    try:
        api_key = ns["API_KEY"]
        api_url = ns["API_URL"]
    except KeyError as e:
        raise SystemExit(f"Credentials file must define API_KEY and API_URL. Missing: {e}")

    return Canvas(api_url, api_key)


def load_meta(folder: Path):
    meta_path = folder / "meta.json"
    if not meta_path.is_file():
        raise ValueError(f"No meta.json in {folder}")
    with meta_path.open(encoding="utf-8") as f:
        return json.load(f)


def find_page(course, title: str):
    for page in course.get_pages():
        if page.title == title:
            return page
    return None


def ensure_module(course, name: str):
    for m in course.get_modules():
        if m.name == name:
            return m
    return course.create_module({"name": name})


def module_has_page(module, page_url: str):
    for item in module.get_module_items():
        if item.type == "Page" and getattr(item, "page_url", None) == page_url:
            return True
    return False


def sync_page(course, folder: Path):
    meta = load_meta(folder)

    if meta.get("type") != "Page":
        return

    mods = meta.get("modules") or []
    if not mods:
        return

    title = meta.get("name")
    if not title:
        print(f"[modules:warn] {folder.name}: missing 'name' in meta.json")
        return

    page = find_page(course, title)
    if not page:
        print(f"[modules:warn] {folder.name}: page '{title}' not found in Canvas")
        return

    page_url = page.url

    for mname in mods:
        module = ensure_module(course, mname)
        if module_has_page(module, page_url):
            print(f"[↻ modules] {folder.name} → {mname}")
            continue
        module.create_module_item(
            {"type": "Page", "page_url": page_url, "title": title}
        )
        print(f"[✓ modules] {folder.name} → {mname}")


if __name__ == "__main__":
    canvas = get_canvas()
    page_folders = list(PAGES_DIR.rglob("*.page"))

    for course_id in COURSE_IDS:
        course = canvas.get_course(course_id)
        for folder in page_folders:
            sync_page(course, folder)
            print()  # blank line between pages
