#!/usr/bin/env python3
"""
sync_rubrics.py

For the current course (cwd):

- Finds all *.assignment folders under pages/
- If rubric.yaml (or .yml/.json) exists in a folder, loads it
- Uses meta.json to identify the assignment in Canvas
- Creates or updates a rubric for that assignment via the Canvas Rubrics API
- Handles both local criteria and outcome-aligned criteria (for assessment)

Assumptions:
- Environment:
    CANVAS_CREDENTIAL_FILE=/home/chapman/.canvas/credentials.txt
    COURSE_ID=<canvas course id>
- Outcome mapping file:
    _course_metadata/outcome_map.json
  with structure:
    { "<outcome_code>": <outcome_id>, ... }
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # pip install pyyaml
from canvasapi import Canvas  # [web:266]
from canvasapi.course import Course  # [web:220]


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSE_ROOT = Path.cwd()
PAGES_DIR = COURSE_ROOT / "pages"
COURSE_META_DIR = COURSE_ROOT / "_course_metadata"
OUTCOME_MAP_PATH = COURSE_META_DIR / "outcome_map.json"


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
        raise SystemExit(f"Credentials file must define API_KEY and API_URL. Missing: {e}")

    return Canvas(api_url, api_key)  # [web:266]


def load_outcome_map() -> Dict[str, int]:
    """
    Load mapping from outcome_code -> outcome_id created by sync_outcomes.py.
    """
    if not OUTCOME_MAP_PATH.is_file():
        print(f"[rubrics:warn] No outcome_map.json at {OUTCOME_MAP_PATH}; outcome-aligned rows will be skipped")
        return {}

    with OUTCOME_MAP_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    # ensure IDs are ints
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
        raise FileNotFoundError(f"No meta.json in {folder}")
    with meta_path.open(encoding="utf-8") as f:
        return json.load(f)


def find_assignment_by_name(course: Course, name: str):
    """
    Find a Canvas assignment with a title matching 'name'.
    This is simple but fits your current workflow.
    """
    for a in course.get_assignments():  # [web:220]
        if a.name == name:
            return a
    return None


def build_rubric_params(
    rubric_spec: Dict[str, Any],
    outcome_map: Dict[str, int],
) -> Dict[str, Any]:
    """
    Build parameters for Course.create_rubric from rubric.yaml + outcome_map.

    rubric_spec example:
      title: "Essay 1 Rubric"
      free_form_comments: false
      criteria:
        - id: "organization"
          kind: "local"
          description: "Organization and coherence"
          ratings:
            - description: "Excellent"
              points: 4
            ...

        - id: "thesis_outcome"
          kind: "outcome"
          outcome_code: "WRIT-THESIS-1"
          use_for_scoring: true
          points: 4
    """
    title = rubric_spec.get("title", "Untitled Rubric")
    free_form_comments = bool(rubric_spec.get("free_form_comments", False))

    criteria_spec = rubric_spec.get("criteria") or []
    if not isinstance(criteria_spec, list):
        raise ValueError("rubric.yaml: 'criteria' must be a list")

    rubric_criteria: Dict[str, Dict[str, Any]] = {}
    idx = 1

    for crit in criteria_spec:
        cid = crit.get("id") or f"crit_{idx}"
        kind = crit.get("kind", "local")

        description = crit.get("description", "")
        long_description = crit.get("long_description", "")
        ratings = crit.get("ratings") or []

        # Canvas expects a hash of RubricCriteria keyed by integer-ish keys. [web:277]
        key = str(idx)
        idx += 1

        crit_params: Dict[str, Any] = {
            "description": description,
            "long_description": long_description,
            "criterion_use_range": False,
        }

        # ratings: list of {description, points}
        if ratings:
            crit_params["ratings"] = []
            for r in ratings:
                crit_params["ratings"].append(
                    {
                        "description": r.get("description", ""),
                        "points": float(r.get("points", 0)),
                    }
                )

        if kind == "outcome":
            # Outcome-aligned row
            code = crit.get("outcome_code")
            if not code:
                print(f"[rubrics:warn] outcome criterion '{cid}' missing outcome_code; treating as local")
            else:
                outcome_id = outcome_map.get(code)
                if not outcome_id:
                    print(f"[rubrics:warn] outcome_code '{code}' not found in outcome_map; treating '{cid}' as local")
                else:
                    # Attach outcome_id, use_for_scoring etc.
                    crit_params["learning_outcome_id"] = int(outcome_id)
                    crit_params["mastery_points"] = crit.get("mastery_points", None)
                    crit_params["use_for_scoring"] = bool(crit.get("use_for_scoring", True))
                    # If points not specified via ratings, allow a top-level points override
                    if "points" in crit and not ratings:
                        crit_params["points"] = float(crit["points"])

        rubric_criteria[key] = crit_params

    params: Dict[str, Any] = {
        "title": title,
        "free_form_criterion_comments": free_form_comments,
        "rubric": {
            "title": title,
            "criteria": rubric_criteria,
        },
    }

    return params


def create_or_update_rubric_for_assignment(
    course: Course,
    assignment,
    rubric_spec: Dict[str, Any],
    outcome_map: Dict[str, int],
):
    """
    Create (or overwrite) a rubric attached to the given assignment.

    Strategy:
    - Always create a new rubric with the given title and criteria, associated to the assignment.
      (Canvas will treat imported outcomes correctly when learning_outcome_id is provided.) [web:282][web:277]
    - We do not attempt in-place diffing; re-create idempotently from the flat spec.
    """
    from canvasapi.course import Course  # type: ignore

    rubric_params = build_rubric_params(rubric_spec, outcome_map)

    # Association params: link rubric to assignment and use for grading if desired. [web:277][web:295]
    assoc_params = {
        "rubric_association": {
            "association_id": assignment.id,
            "association_type": "Assignment",
            "use_for_grading": True,
            "purpose": "grading",
            "title": assignment.name,
        }
    }

    merged = {**rubric_params, **assoc_params}

    print(f"[rubrics] Creating rubric '{rubric_params['title']}' for assignment '{assignment.name}'")

    # canvasapi Course.create_rubric wraps POST /courses/:course_id/rubrics. [web:315]
    result = course.create_rubric(**merged)
    # result is a dict with 'rubric' and 'rubric_association' keys. [web:315]
    rubric = result.get("rubric")
    assoc = result.get("rubric_association")
    print(f"[rubrics:ok] rubric_id={getattr(rubric, 'id', '?')} assoc_id={getattr(assoc, 'id', '?')}")


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

    # Find assignment in Canvas by name
    assignment = find_assignment_by_name(course, name)
    if not assignment:
        print(f"[rubrics:err] {folder.name}: assignment '{name}' not found in Canvas")
        return

    # Load rubric spec
    try:
        if rubric_file.suffix.lower() in [".yaml", ".yml"]:
            with rubric_file.open(encoding="utf-8") as f:
                rubric_spec = yaml.safe_load(f) or {}
        elif rubric_file.suffix.lower() == ".json":
            with rubric_file.open(encoding="utf-8") as f:
                rubric_spec = json.load(f)
        else:
            print(f"[rubrics:err] {folder.name}: unsupported rubric file extension '{rubric_file.suffix}'")
            return
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to parse {rubric_file.name}: {e}")
        return

    try:
        create_or_update_rubric_for_assignment(course, assignment, rubric_spec, outcome_map)
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to create/update rubric: {e}")


def main():
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    canvas = load_canvas()
    course = canvas.get_course(int(course_id))  # [web:220]

    outcome_map = load_outcome_map()

    assignment_folders = iter_assignment_folders()
    if not assignment_folders:
        print(f"[rubrics] No *.assignment folders found under {PAGES_DIR}")
        return

    for folder in assignment_folders:
        process_assignment_folder(course, folder, outcome_map)
        print()  # blank line between folders


if __name__ == "__main__":
    main()
