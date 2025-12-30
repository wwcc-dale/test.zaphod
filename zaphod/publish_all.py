#!/usr/bin/env python3
from pathlib import Path
import os
import json
import re


import markdown2canvas as mc
from markdown2canvas import canvas_objects
from markdown2canvas.setup_functions import make_canvas_api_obj  # [web:131]


# Import get_course_id from your shared config_utils
from config_utils import get_course_id


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



# {{video:filename}} regex (with optional quotes)
VIDEO_RE = re.compile(r"\{\{video:\s*\"?([^}\"]+?)\"?\s*\}\}")

def get_or_upload_video_file(course, folder: Path, filename: str):
    """
    Return a canvasapi File object for `filename` in this course.
    If not found by name, upload from `folder/filename`.
    """
    # 1) Search existing files by name
    for f in course.get_files(search_term=filename):
        if f.display_name == filename or f.filename == filename:
            return f


    # 2) Upload from local disk if not found
    local_path = folder / filename
    if not local_path.is_file():
        raise FileNotFoundError(f"Video file not found: {local_path}")


    # Upload via Canvas API
    success, resp = course.upload(str(local_path))
    if not success:
        raise RuntimeError(f"Upload failed for {local_path}: {resp}")


    file_id = resp.get("id")
    if not file_id:
        raise RuntimeError(f"No file id in upload response for {local_path}: {resp}")


    # Return a File object
    return course.get_file(file_id)



def replace_video_placeholders(text: str, course, folder: Path, canvas_base_url: str) -> str:
    """
    Replace {{video:filename}} or {{video:"filename with spaces"}} with a Canvas media-attachment iframe.
    """
    def replace(match):
        raw = match.group(1).strip()
        try:
            f = get_or_upload_video_file(course, folder, raw)
        except Exception as e:
            print(f"[publish:warn] {folder.name}: video '{raw}': {e}")
            return match.group(0)


        # Use Canvas media_attachments_iframe URL
        src = f"{canvas_base_url}/media_attachments_iframe/{f.id}"


        return (
            f'<iframe style="width: 480px; height: 300px; display: inline-block;" '
            f'title="Video player for {f.display_name}" '
            f'data-media-type="video" '
            f'src="{src}" '
            f'loading="lazy" '
            f'allowfullscreen="allowfullscreen" '
            f'allow="fullscreen"></iframe>'
        )


    result = VIDEO_RE.sub(replace, text)
    print(f"[debug] Final text length: {len(result)}")
    print(f"[debug] Final text contains media_attachments_iframe: {'media_attachments_iframe' in result}")
    return result



# Set up Canvas API
canvas = make_canvas_api_obj()  # uses CANVAS_CREDENTIAL_FILE [web:131]


# Get Canvas base URL from environment or config
# Adjust this to match how make_canvas_api_obj() gets the base URL
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.instructure.com")


# Get the single course ID for this course
course_id = get_course_id(course_dir=COURSE_ROOT)
if course_id is None:
    raise SystemExit("[publish] Cannot determine Canvas course ID; aborting.")


# Make it a single-item list to keep the existing loop structure
COURSE_IDS = [course_id]



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
                print(f"[debug] Processing {d.name} as {type(obj).__name__}")


                # Only Pages and Assignments have source.md
                if isinstance(obj, (mc.Page, mc.Assignment)):
                    source_md = d / "source.md"
                    if source_md.is_file():
                        text = source_md.read_text(encoding="utf-8")
                        print(f"[debug] {d.name}: read source.md ({len(text)} chars)")
                        text = replace_video_placeholders(text, course, d, CANVAS_BASE_URL)
                        print(f"[debug] {d.name}: after video replacement ({len(text)} chars)")
                        source_md.write_text(text, encoding="utf-8")
                        print(f"[debug] {d.name}: wrote modified source.md")
                    else:
                        print(f"[debug] {d.name}: source.md not found")


                obj.publish(course, overwrite=True)
                print(f"[✓ publish] {d.name}")
            except Exception as e:
                print(f"[publish:err] {d.name}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
            print()
