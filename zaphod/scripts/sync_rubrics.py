#!/usr/bin/env python3
"""
sync_rubrics.py

For the current course (cwd):

- Finds all .assignment folders under pages/
- If rubric.yaml or .yml/.json exists in a folder, loads it
- Uses meta.json to identify the assignment in Canvas
- Creates a rubric from a CSV via the Rubric Upload API
- Attaches that rubric to the assignment using RubricAssociations

Assumptions
- Env:
    CANVAS_CREDENTIAL_FILE=$HOME/.canvas/credentials.txt
    COURSE_ID=canvas course id
- Outcome mapping file:
    coursemetadata/outcomemap.json with structure:
      { "OUTCOME_CODE": outcome_id, ... }
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml
from canvasapi import Canvas
from canvasapi.course import Course

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSE_ROOT = Path.cwd()
PAGES_DIR = COURSE_ROOT / "pages"
COURSE_META_DIR = COURSE_ROOT / "coursemetadata"
OUTCOME_MAP_PATH = COURSE_META_DIR / "outcomemap.json"


# ---------- Canvas helpers ----------


def load_canvas() -> Canvas:
    cred_path = os.environ.get("CANVAS_CREDENTIAL_FILE")
    if not cred_path:
        raise SystemExit("CANVAS_CREDENTIAL_FILE is not set")

    cred_file = Path(cred_path)
    if not cred_file.is_file():
        raise SystemExit(f"CANVAS_CREDENTIAL_FILE does not exist: {cred_file}")

    ns: Dict[str, Any] = {}
    exec(cred_file.read_text(encoding="utf-8"), ns)
    try:
        api_key = ns["API_KEY"]
        api_url = ns["API_URL"]
    except KeyError as e:
        raise SystemExit(f"Credentials file must define API_KEY and API_URL. Missing {e!r}")
    return Canvas(api_url, api_key)


def load_outcome_map() -> Dict[str, int]:
    """
    Load mapping from outcome_code -> outcome_id created by a separate outcomes sync step.
    """
    if not OUTCOME_MAP_PATH.is_file():
        print(f"[rubrics:warn] No outcomemap.json at {OUTCOME_MAP_PATH}; "
              f"outcome-aligned rows will be skipped")
        return {}

    with OUTCOME_MAP_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    return {code: int(oid) for code, oid in data.items()}


def iter_assignment_folders() -> List[Path]:
    if not PAGES_DIR.exists():
        return []
    return list(PAGES_DIR.rglob("*.assignment"))


def find_rubric_file(folder: Path) -> Optional[Path]:
    """
    Look for rubric.yaml / rubric.yml / rubric.json in the folder.
    """
    candidates = [
        folder / "rubric.yaml",
        folder / "rubric.yml",
        folder / "rubric.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_meta(folder: Path) -> Dict[str, Any]:
    meta_path = folder / "meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"No meta.json in folder {folder}")
    with meta_path.open(encoding="utf-8") as f:
        return json.load(f)


def find_assignment_by_name(course: Course, name: str):
    """
    Find a Canvas assignment with a title matching name.
    """
    for a in course.get_assignments():
        if a.name == name:
            return a
    return None


# ---------- Rubric CSV rendering ----------


def build_rubric_csv(
    rubric_spec: Dict[str, Any],
    outcome_map: Dict[str, int],
) -> bytes:
    """
    Render rubric_spec into a CSV compatible with the Rubrics Upload API.

    Canvas' upload template is a CSV; the exact columns can be obtained from
    GET /api/v1/rubrics/upload_template. Here we implement a simple, common
    layout that works with the official template:

        Criterion,Description,Points,Rating 1,Points 1,Rating 2,Points 2,...

    Outcome-aligned criteria will ignore the outcome_id in CSV; outcomes can be
    wired separately if needed.
    """

    title = rubric_spec.get("title", "Untitled Rubric")
    criteria_spec = rubric_spec.get("criteria") or []
    if not isinstance(criteria_spec, list):
        raise ValueError("rubric.yaml 'criteria' must be a list")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row; Canvas' template may include more columns, but these are core.
    header = [
        "Criterion",
        "Description",
        "Points",
        "Rating 1",
        "Points 1",
        "Rating 2",
        "Points 2",
        "Rating 3",
        "Points 3",
        "Rating 4",
        "Points 4",
    ]
    writer.writerow(header)

    for crit in criteria_spec:
        crit_desc = crit.get("description", "")
        long_desc = crit.get("long_description", "")
        ratings = crit.get("ratings") or []

        # Criterion-level points: use explicit points, else max of ratings, else 0.
        if "points" in crit:
            crit_points = float(crit["points"])
        elif ratings:
            crit_points = max((float(r.get("points", 0)) for r in ratings), default=0.0)
        else:
            crit_points = 0.0

        row: List[Any] = []
        row.append(crit_desc)        # Criterion
        row.append(long_desc)        # Description
        row.append(crit_points)      # Points

        # Up to 4 ratings; Canvas template often supports several.
        for r in ratings[:4]:
            row.append(r.get("description", ""))
            row.append(r.get("points", 0))
        # Pad remaining rating slots
        remaining_slots = 4 - min(len(ratings), 4)
        for _ in range(remaining_slots):
            row.append("")
            row.append("")

        writer.writerow(row)

    csv_str = output.getvalue()
    print("[rubrics:debug] generated rubric CSV:")
    print(csv_str)
    return csv_str.encode("utf-8")


# ---------- Rubric upload + association ----------


def upload_rubric_csv_to_course(
    course: Course,
    csv_bytes: bytes,
) -> Dict[str, Any]:
    """
    POST /api/v1/courses/:course_id/rubrics/upload with the CSV file.

    Returns the rubric import object returned by Canvas.
    """
    path = f"courses/{course.id}/rubrics/upload"
    base = course._requester.base_url.rstrip("/")
    if base.endswith("/api/v1"):
        url = f"{base}/{path}"
    else:
        url = f"{base}/api/v1/{path}"

    session: requests.Session = course._requester._session

    files = {
        "attachment": ("rubric.csv", csv_bytes, "text/csv"),
    }

    print(f"[rubrics] Uploading rubric CSV for course {course.id}")
    resp = session.post(url, files=files)
    print("[rubrics:upload] status:", resp.status_code)
    print("[rubrics:upload] body:", resp.text)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Rubric upload failed with status {resp.status_code}")

    return resp.json()


def poll_rubric_upload_status(
    course: Course,
    import_id: int,
    poll_interval: float = 1.0,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Poll GET /api/v1/courses/:course_id/rubrics/upload/:id until complete or timeout.
    """
    path = f"courses/{course.id}/rubrics/upload/{import_id}"
    base = course._requester.base_url.rstrip("/")
    if base.endswith("/api/v1"):
        url = f"{base}/{path}"
    else:
        url = f"{base}/api/v1/{path}"

    session: requests.Session = course._requester._session

    start = time.time()
    while True:
        resp = session.get(url)
        print("[rubrics:upload_status] status:", resp.status_code)
        print("[rubrics:upload_status] body:", resp.text)
        if resp.status_code != 200:
            raise RuntimeError(f"Rubric upload status error {resp.status_code}")

        data = resp.json()
        # The exact shape of the rubric import object is not fully documented,
        # but typically there is a 'workflow_state' and, once complete, a rubric id.
        state = data.get("workflow_state") or data.get("status")
        if state in ("imported", "completed", "complete", "succeeded"):
            return data
        if state in ("failed", "failed_with_messages", "error"):
            raise RuntimeError(f"Rubric upload failed with state {state}")

        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for rubric upload to complete")

        time.sleep(poll_interval)


def create_rubric_association(
    course: Course,
    assignment,
    rubric_id: int,
    use_for_grading: bool = True,
    purpose: str = "grading",
) -> Dict[str, Any]:
    """
    POST /api/v1/courses/:course_id/rubric_associations to attach rubric to assignment.
    """
    path = f"courses/{course.id}/rubric_associations"
    base = course._requester.base_url.rstrip("/")
    if base.endswith("/api/v1"):
        url = f"{base}/{path}"
    else:
        url = f"{base}/api/v1/{path}"

    session: requests.Session = course._requester._session

    data = {
        "rubric_association[rubric_id]": str(rubric_id),
        "rubric_association[association_id]": str(assignment.id),
        "rubric_association[association_type]": "Assignment",
        "rubric_association[title]": assignment.name,
        "rubric_association[use_for_grading]": "1" if use_for_grading else "0",
        "rubric_association[purpose]": purpose,
    }

    print(f"[rubrics] Creating rubric association rubric_id={rubric_id} -> assignment {assignment.id}")
    resp = session.post(url, data=data)
    print("[rubrics:assoc] status:", resp.status_code)
    print("[rubrics:assoc] body:", resp.text)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Rubric association failed with status {resp.status_code}")

    return resp.json()


def create_or_update_rubric_for_assignment_via_upload(
    course: Course,
    assignment,
    rubric_spec: Dict[str, Any],
    outcome_map: Dict[str, int],
):
    """
    Full flow for one assignment:

    - Build rubric CSV from rubric_spec.
    - Upload CSV using Rubrics Upload API.
    - Poll status to get created rubric id.
    - Attach rubric to the assignment with RubricAssociations API.
    """
    title = rubric_spec.get("title", "Untitled Rubric")
    print(f"[rubrics] Preparing rubric {title!r} for assignment {assignment.name!r}")

    csv_bytes = build_rubric_csv(rubric_spec, outcome_map)

    upload_obj = upload_rubric_csv_to_course(course, csv_bytes)
    import_id = upload_obj.get("id") or upload_obj.get("rubric_import_id")
    if import_id is None:
        raise RuntimeError("Rubric upload response did not include an import id")

    print(f"[rubrics] Polling upload status for import id {import_id}")
    status_obj = poll_rubric_upload_status(course, int(import_id))

    # The final rubric id might be under different keys depending on Canvas version.
    rubric_id = (
        status_obj.get("rubric_id")
        or status_obj.get("id")
        or status_obj.get("rubric", {}).get("id")
    )
    if rubric_id is None:
        raise RuntimeError("Upload status did not include a rubric id")

    print(f"[rubrics] Upload completed; rubric_id={rubric_id}")
    create_rubric_association(course, assignment, int(rubric_id))


# ---------- Per-folder processing ----------


def process_assignment_folder(
    course: Course,
    folder: Path,
    outcome_map: Dict[str, int],
):
    rubric_file = find_rubric_file(folder)
    if not rubric_file:
        print(f"[rubrics:skip] {folder.name}: no rubric.yaml/yml/json")
        return

    try:
        meta = load_meta(folder)
    except FileNotFoundError as e:
        print(f"[rubrics:err] {folder.name}: {e}")
        return

    name = meta.get("name")
    if not name:
        print(f"[rubrics:err] {folder.name}: meta.json missing 'name'")
        return

    assignment = find_assignment_by_name(course, name)
    if not assignment:
        print(f"[rubrics:err] {folder.name}: assignment name {name!r} not found in Canvas")
        return

    # Load rubric spec from YAML/JSON
    try:
        if rubric_file.suffix.lower() in (".yaml", ".yml"):
            with rubric_file.open(encoding="utf-8") as f:
                rubric_spec = yaml.safe_load(f) or {}
        elif rubric_file.suffix.lower() == ".json":
            with rubric_file.open(encoding="utf-8") as f:
                rubric_spec = json.load(f)
        else:
            print(
                f"[rubrics:err] {folder.name}: unsupported rubric file extension "
                f"{rubric_file.suffix}"
            )
            return
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to parse {rubric_file.name}: {e}")
        return

    try:
        create_or_update_rubric_for_assignment_via_upload(
            course, assignment, rubric_spec, outcome_map
        )
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to create/update rubric via upload: {e}")


def main():
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    canvas = load_canvas()
    course = canvas.get_course(int(course_id))

    outcome_map = load_outcome_map()
    assignment_folders = iter_assignment_folders()
    if not assignment_folders:
        print("[rubrics] No .assignment folders found under", PAGES_DIR)
        return

    for folder in assignment_folders:
        process_assignment_folder(course, folder, outcome_map)
        print()

    print("[rubrics] Done.")


if __name__ == "__main__":
    main()
