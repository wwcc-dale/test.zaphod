#!/usr/bin/env python3
from pathlib import Path
import markdown2canvas as mc

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # always “current course”
PAGES_DIR = COURSE_ROOT / "pages" # where applicable

# Optional: disable buggy module handling inside markdown2canvas
from markdown2canvas import canvas_objects

def _no_modules(self, course):
    return None

canvas_objects.Page.ensure_in_modules = _no_modules
canvas_objects.Assignment.ensure_in_modules = _no_modules
canvas_objects.Link.ensure_in_modules = _no_modules
canvas_objects.File.ensure_in_modules = _no_modules

# Discover all content directories
content_dirs = []
for ext in [".page", ".assignment", ".link", ".file"]:
    content_dirs.extend(PAGES_DIR.rglob(f"*{ext}"))


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


from markdown2canvas.setup_functions import make_canvas_api_obj

canvas = make_canvas_api_obj()  # uses CANVAS_CREDENTIAL_FILE
COURSE_IDS = [1259205]  # your Canvas course ID(s)

if __name__ == "__main__":
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
