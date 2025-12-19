#!/usr/bin/env python3
"""
prune_canvas_content.py

Reconcile Canvas pages/assignments against the current Zaphod/markdown2canvas
flat-file repo, deleting items that no longer exist locally.

Safety:
- Default is dry-run (no deletions).
- Use --apply to actually delete.
- Matching is by exact title/name.
"""

from pathlib import Path
import argparse
import json

from markdown2canvas.setup_functions import make_canvas_api_obj
from markdown2canvas.exception import DoesntExist  # if you want to reuse it


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()          # current course
PAGES_DIR = COURSE_ROOT / "pages"


def load_local_names():
    """Return (page_names, assignment_names) from local meta.json files."""
    page_names = set()
    assignment_names = set()

    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")

    for meta_path in PAGES_DIR.rglob("meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] Skipping {meta_path}: failed to parse JSON ({e})")
            continue

        t = str(data.get("type", "")).lower()
        name = data.get("name")
        if not name:
            print(f"[warn] {meta_path} has no 'name'; skipping")
            continue

        if t == "page":
            page_names.add(name)
        elif t == "assignment":
            assignment_names.add(name)

    return page_names, assignment_names


def load_canvas_sets(course):
    """Return (canvas_page_names, canvas_assignment_names) for the course."""
    canvas_page_names = {p.title for p in course.get_pages()}
    canvas_assignment_names = {a.name for a in course.get_assignments()}
    return canvas_page_names, canvas_assignment_names


def delete_extra_pages(course, extra_pages, apply=False):
    """Delete or report Canvas pages that are not in the repo."""
    if not extra_pages:
        print("No extra pages to delete.")
        return

    print("\nExtra Canvas pages (not present in repo):")
    for title in sorted(extra_pages):
        print(f"  - {title}")

    if not apply:
        print("\nDry-run only (no deletions). Re-run with --apply to delete.")
        return

    print("\nDeleting extra pages...")
    for page in course.get_pages():
        if page.title in extra_pages:
            try:
                print(f"  deleting page: {page.title}")
                page.delete()
            except Exception as e:
                print(f"  [err] failed to delete page '{page.title}': {e}")


def delete_extra_assignments(course, extra_assignments, apply=False):
    """Delete or report Canvas assignments that are not in the repo."""
    if not extra_assignments:
        print("No extra assignments to delete.")
        return

    print("\nExtra Canvas assignments (not present in repo):")
    for name in sorted(extra_assignments):
        print(f"  - {name}")

    if not apply:
        print("\nDry-run only (no deletions). Re-run with --apply to delete.")
        return

    print("\nDeleting extra assignments...")
    for a in course.get_assignments():
        if a.name in extra_assignments:
            try:
                print(f"  deleting assignment: {a.name}")
                a.delete()
            except Exception as e:
                print(f"  [err] failed to delete assignment '{a.name}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Prune Canvas pages/assignments not present in the local Zaphod repo."
    )
    parser.add_argument(
        "--course-id",
        type=int,
        help="Canvas course ID (optional if you hard-code or use env in make_canvas_api_obj).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete extra items on Canvas. Without this, runs in dry-run mode.",
    )
    parser.add_argument(
        "--include-assignments",
        action="store_true",
        help="Also prune assignments (not just pages).",
    )
    args = parser.parse_args()

    # Connect to Canvas via markdown2canvas helper (uses CANVAS_CREDENTIAL_FILE env).[file:11]
    canvas = make_canvas_api_obj()

    if args.course_id:
        course_id = args.course_id
    else:
        # If you normally use an env var COURSEID elsewhere, you can mirror that here:
        import os
        env_course = os.environ.get("COURSEID")
        if not env_course:
            raise SystemExit("COURSEID not set and --course-id not provided.")
        course_id = int(env_course)

    course = canvas.get_course(course_id)
    print(f"Pruning against course: {course.name} (ID {course_id})")

    local_page_names, local_assignment_names = load_local_names()
    canvas_page_names, canvas_assignment_names = load_canvas_sets(course)

    extra_pages = canvas_page_names - local_page_names
    extra_assignments = canvas_assignment_names - local_assignment_names

    delete_extra_pages(course, extra_pages, apply=args.apply)

    if args.include_assignments:
        delete_extra_assignments(course, extra_assignments, apply=args.apply)
    else:
        if extra_assignments:
            print(
                "\nAssignments with no local counterpart exist, "
                "but --include-assignments was not set, so they were not deleted."
            )


if __name__ == "__main__":
    main()
