#!/usr/bin/env python3
"""
# Zaphod
# Copyright (c) 2026 Dale Chapman
# Licensed under the MIT License. See LICENSE in the project root.

sync_rubrics.py

For the current course (cwd):

- Finds all .assignment folders under pages/
- If rubric.yaml / rubric.yml / rubric.json exists in a folder, loads it (YAML/JSON)
- Uses meta.json to identify the assignment in Canvas
- Creates a rubric via the Rubrics API from the YAML/JSON spec
- Associates that rubric with the assignment using RubricAssociations semantics

Assumptions
- Run from course root (where pages/ lives).
- Env:
    CANVAS_CREDENTIAL_FILE=$HOME/.canvas/credentials.txt
    COURSE_ID=canvas course id
- Credentials file defines:
    API_KEY = "..."
    API_URL = "https://yourcanvas.institution.edu"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
import yaml
from config_utils import get_course_id
from canvasapi import Canvas
from canvasapi.course import Course

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSE_ROOT = Path.cwd()
PAGES_DIR = COURSE_ROOT / "pages"


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


def get_api_url_and_key() -> tuple[str, str]:
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
    return api_url.rstrip("/"), api_key


# ---------- Local file helpers ----------

def iter_assignment_folders_with_rubrics() -> List[Path]:
    """
    Find all .assignment folders that contain a rubric file.
    """
    if not PAGES_DIR.exists():
        return []

    folders: List[Path] = []
    for folder in PAGES_DIR.rglob("*.assignment"):
        if not folder.is_dir():
            continue
        if find_rubric_file(folder) is not None:
            folders.append(folder)
    return folders


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


# ---------- Rubric YAML/JSON loading ----------

def load_rubric_spec(path: Path) -> Dict[str, Any]:
    """
    Load rubric spec from YAML or JSON file.
    """
    try:
        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        elif path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"Unsupported rubric file extension {path.suffix}")
    except Exception as e:
        raise RuntimeError(f"Failed to parse rubric file {path}: {e}")


def build_rubric_payload(
    rubric: Dict[str, Any],
    assignment,
) -> Dict[str, Any]:
    """
    Turn a rubric spec (YAML/JSON) into the form fields expected by
    POST /api/v1/courses/:course_id/rubrics, associating it with an assignment.[web:549][web:551]
    """
    title = rubric.get("title")
    if not title:
        raise SystemExit("Rubric spec must define 'title'.")

    free_form = bool(rubric.get("free_form_criterion_comments", False))

    criteria = rubric.get("criteria") or []
    if not criteria:
        raise SystemExit("Rubric spec must define a non-empty 'criteria' list.")

    assoc_cfg = rubric.get("association") or {}
    # Association is always to an Assignment in this script
    assoc_type = "Assignment"
    assoc_id = str(assoc_cfg.get("id") or assignment.id)
    assoc_purpose = assoc_cfg.get("purpose", "grading")
    assoc_use_for_grading = bool(assoc_cfg.get("use_for_grading", True))

    data: Dict[str, Any] = {
        "title": title,
        "rubric_id": "new",
        "rubric[title]": title,
        "rubric[free_form_criterion_comments]": "1" if free_form else "0",
        "rubric_association[association_type]": assoc_type,
        "rubric_association[association_id]": assoc_id,
        "rubric_association[use_for_grading]": "1" if assoc_use_for_grading else "0",
        "rubric_association[purpose]": assoc_purpose,
        "rubric_association[title]": assignment.name,
    }

    for i, crit in enumerate(criteria):
        c_desc = crit.get("description")
        c_long = crit.get("long_description", "")
        c_points = crit.get("points")
        c_use_range = bool(crit.get("use_range", False))
        ratings = crit.get("ratings") or []

        if c_desc is None or c_points is None or not ratings:
            raise SystemExit(
                f"Criterion {i} must define 'description', 'points', and non-empty 'ratings'."
            )

        base = f"rubric[criteria][{i}]"
        data[f"{base}[description]"] = str(c_desc)
        data[f"{base}[long_description]"] = str(c_long)
        data[f"{base}[points]"] = str(c_points)
        data[f"{base}[criterion_use_range]"] = "1" if c_use_range else "0"

        for j, rating in enumerate(ratings):
            r_desc = rating.get("description")
            r_long = rating.get("long_description", "")
            r_points = rating.get("points")
            if r_desc is None or r_points is None:
                raise SystemExit(
                    f"Criterion {i} rating {j} must define 'description' and 'points'."
                )
            rbase = f"{base}[ratings][{j}]"
            data[f"{rbase}[description]"] = str(r_desc)
            data[f"{rbase}[long_description]"] = str(r_long)
            data[f"{rbase}[points]"] = str(r_points)

    return data


# ---------- Rubric creation ----------

def create_rubric_via_api(
    course_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    POST /api/v1/courses/:course_id/rubrics using the provided payload.[web:549][web:551]
    """
    api_url, api_key = get_api_url_and_key()

    url = f"{api_url}/api/v1/courses/{course_id}/rubrics"
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = requests.post(url, headers=headers, data=payload)
    # print("[rubrics] POST", url)
    # print("[rubrics] Status:", resp.status_code)
    # print("[rubrics] Body:", resp.text)

    if resp.status_code in (200, 201):
        return resp.json()
    if resp.status_code in (401, 403):
        raise RuntimeError("Not authorized to create rubrics (token/role lacks permission).")
    if resp.status_code == 404:
        raise RuntimeError("Rubrics endpoint not reachable (bad course id, base URL, or API disabled).")
    if resp.status_code == 422:
        raise RuntimeError(f"Rubric validation error (422): {resp.text}")
    raise RuntimeError(f"Unexpected status {resp.status_code}: {resp.text}")


# ---------- Per-folder processing ----------

def process_assignment_folder(course: Course, folder: Path):
    rubric_file = find_rubric_file(folder)
    if not rubric_file:
        print(f"[rubrics:skip] {folder.name}: no rubric.yaml/yml/json")
        return

    try:
        meta = load_meta(folder)
    except FileNotFoundError as e:
        print(f"[rubrics:err] {folder.name}: {e}")
        return

    ctype = str(meta.get("type", "")).lower()
    name = meta.get("name")

    if ctype != "assignment":
        print(f"[rubrics:skip] {folder.name}: meta.type is {ctype!r}, expected 'assignment'")
        return

    if not name:
        print(f"[rubrics:err] {folder.name}: meta.json missing 'name'")
        return

    assignment = find_assignment_by_name(course, name)
    if not assignment:
        print(f"[rubrics:err] {folder.name}: assignment name {name!r} not found in Canvas")
        return

    print(f"[rubrics] Processing {folder.name}: associating rubric to assignment {assignment.id} ({assignment.name})")

    try:
        rubric_spec = load_rubric_spec(rubric_file)
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to load rubric spec: {e}")
        return

    try:
        payload = build_rubric_payload(rubric_spec, assignment)
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: invalid rubric spec: {e}")
        return

    try:
        result = create_rubric_via_api(str(course.id), payload)
        rubric = result.get("rubric") or {}
        rubric_id = rubric.get("id")
        print(f"[rubrics] Created rubric id={rubric_id} for assignment {assignment.id}")
    except Exception as e:
        print(f"[rubrics:err] {folder.name}: failed to create rubric: {e}")


# ---------- Main ----------

def main():
    course_id = get_course_id()
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")

    canvas = load_canvas()
    course = canvas.get_course(int(course_id))

    folders = iter_assignment_folders_with_rubrics()
    if not folders:
        print("[rubrics] No .assignment folders with rubric.yaml found under", PAGES_DIR)
        return

    print(f"[rubrics] Syncing rubrics for course {course.name} (ID {course_id})")
    for folder in folders:
        process_assignment_folder(course, folder)
        print()

    print("[rubrics] Done.")


if __name__ == "__main__":
    main()