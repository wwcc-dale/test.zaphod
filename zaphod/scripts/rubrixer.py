#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import requests
import yaml


def load_canvas_creds():
    cred_path = os.environ.get("CANVAS_CREDENTIAL_FILE")
    if not cred_path:
        raise SystemExit("CANVAS_CREDENTIAL_FILE is not set")

    cred_file = Path(cred_path)
    if not cred_file.is_file():
        raise SystemExit(f"CANVAS_CREDENTIAL_FILE does not exist: {cred_file}")

    ns = {}
    exec(cred_file.read_text(encoding="utf-8"), ns)
    try:
        api_url = ns["API_URL"]
        api_key = ns["API_KEY"]
    except KeyError as e:
        raise SystemExit(f"Credentials file must define API_URL and API_KEY. Missing {e!r}")
    return api_url.rstrip("/"), api_key


def load_rubric_yaml(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"Rubric YAML not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit("Rubric YAML must contain a mapping at the top level.")
    return data


def build_rubric_payload(rubric: dict, course_id_env: str) -> dict:
    title = rubric.get("title")
    if not title:
        raise SystemExit("Rubric YAML must define 'title'.")

    free_form = bool(rubric.get("free_form_criterion_comments", False))

    criteria = rubric.get("criteria") or []
    if not criteria:
        raise SystemExit("Rubric YAML must define a non-empty 'criteria' list.")

    association_cfg = rubric.get("association") or {}
    assoc_type = association_cfg.get("type", "Course")
    assoc_id = association_cfg.get("id") or course_id_env
    assoc_purpose = association_cfg.get("purpose", "grading")
    assoc_use_for_grading = bool(association_cfg.get("use_for_grading", False))

    data = {
        "title": title,
        "rubric_id": "new",
        "rubric[title]": title,
        "rubric[free_form_criterion_comments]": "1" if free_form else "0",
        "rubric_association[association_type]": assoc_type,
        "rubric_association[association_id]": str(assoc_id),
        "rubric_association[use_for_grading]": "1" if assoc_use_for_grading else "0",
        "rubric_association[purpose]": assoc_purpose,
    }

    # Build criteria and ratings: rubric[criteria][i][...]
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


def push_rubric(yaml_path: Path):
    api_url, api_key = load_canvas_creds()
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    rubric_cfg = load_rubric_yaml(yaml_path)
    payload = build_rubric_payload(rubric_cfg, course_id_env=course_id)

    url = f"{api_url}/api/v1/courses/{course_id}/rubrics"
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = requests.post(url, headers=headers, data=payload)
    print("Status:", resp.status_code)
    print("Body:", resp.text)

    if resp.status_code in (401, 403):
        print("Not authorized to create rubrics (token/role lacks permission).")
    elif resp.status_code == 404:
        print("Rubrics endpoint not reachable (bad course id, base URL, or API disabled).")
    elif resp.status_code in (200, 201):
        print("Rubrics API usable; rubric created successfully.")
    elif resp.status_code == 422:
        print("Rubrics API reachable; payload needs adjustment (validation error).")
    else:
        print(f"Unexpected status {resp.status_code}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} path/to/rubric.yaml")
    push_rubric(Path(sys.argv[1]))
