# Zaphod
##### A version‑controlled, automatable course authoring environment that’s faster, safer, and more reusable than editing directly in Canvas.

Zaphod is a flat‑file Canvas course workflow where you author course pages, assignments, quizzes, rubrics and outcomes and as structured text (markdown or yaml). Each course can be placed under collaborative version control using Git. Python scripts translate and publish these text files to Canvas. where they become pages and assignments that may include rubrics associated with outcomes and be placed in modules. Quizzes in plain text shorthand (using NYIT‑style) become Classic Quizzes.

---
## Key Benefits
Working from flat files gives you version control, automation, and consistency that are hard to get when authoring directly in the Canvas UI.

#### Collaboration and version control

- Authors can store all content in Git, making it easy to visualize differences between edits, review changes, revert mistakes, and work safely in branches before merging.
- Multiple instructors or designers can collaborate on the same course without overwriting each other’s edits, while maintaing a permanent history of who changed what, and when.

#### Faster editing and reuse

- Markdown and structured text are much faster to edit than a web rich‑text editor, especially for technical content, code blocks, repetitive layouts, and bulk text changes.
- You can copy, refactor, and reuse modules, pages, assignments, quizzes, and rubrics across courses or terms by cloning or templating files rather than rebuilding in the browser.

#### Automation and consistency

- Scripts can enforce consistent metadata (naming, modules, outcomes, topics) and generate pages, outcomes, rubrics, and quizzes in one pass, reducing manual clicking and error risk.
- Global changes (e.g., institution‑wide footers, updated links, replacements variable like `==course-name== ==course-code==`) can be applied across the course(s) by editing one style or replacements file.

#### Portability and longevity

- Content lives in plain text, independent of any given LMS; you can repurpose it for other platforms, static sites, or documentation without scraping Canvas.
- Because the structure is explicit (folders, YAML frontmatter, quiz banks), the same repository can drive multiple Canvas shells, sandboxes, or future LMS migrations.

#### Testing and safety

- instructors can run a local or staging publish (to a test course) and verify everything before pushing to a live section, instead of experimenting directly in a production Canvas course.
- Automated scripts (like Zaphod’s watcher and publish tools) reduce the chance of partial updates or missed pages compared with manual UI edits.


***

## 1. Layout and metadata

```text
/path/to/courses/
  example-course/
    pages/
      intro.page/
        index.md
        meta.json
        source.md
      example.assignment/
        index.md
        meta.json
        source.md
        rubric.yaml
    quiz-banks/
      week1.quiz.txt
      midterm.quiz.txt
    _course_metadata/
      defaults.json
      _styles/
        general/
          header.html
          header.md
          footer.md
          footer.html
        custom/
          header.html
          header.md
          footer.md
          footer.html
      _replacements/
        default.json
      outcomes.yaml
      outcomes_import.csv
      outcome_map.json
    scripts/
      frontmatter_to_meta.py
      publish_all.py
      sync_modules.py
      sync_clo_via_csv.py
      sync_rubrics.py
      sync_quiz_banks.py
      watch_and_publish.py
    .venv/
```

- `pages/*.page` and `pages/*.assignment` hold Canvas course pages and assignments.
- `quiz-banks/*.quiz.txt` holds Classic Quiz definitions, one quiz per file
- `_course_metadata` centralizes style, replacements, outcomes, and imports.

***

## 2. Authoring pages and assignments

#### 2.1 index.md frontmatter

**Page example:**

```markdown
---
name: "Course Introduction"
type: "Page"
modules:
  - "Module 1: Getting Started"
published: true
---

# Course Introduction

This is an example course introduction page.
```

**Assignment example:**

```markdown
---
name: "Example Assignment"
type: "Assignment"
modules:
  - "Module 1: Getting Started"
published: true
---

# Example Assignment

Instructions for the assignment go here.
```

Required fields are `name` and `type`; `modules` and `published` are optional.[1]

#### 2.2 Auto generated work files (meta.json and source.md)

`frontmatter_to_meta.py` generates `meta.json` and `source.md` from `index.md`, for example

```json
{
  "name": "Course Introduction",
  "type": "Page",
  "modules": ["Module 1: Getting Started"],
  "published": true
}
```

`source.md` contains the Markdown body without front matter.

***

## 3. Styles and Replacements

#### 3.1 defaults.json

`_course_metadata/defaults.json` configures style, Markdown extensions, and replacements:

```json
{
  "style": "_styles/general",
  "markdown_extensions": [
    "codehilite",
    "fenced_code",
    "md_in_html",
    "tables",
    "nl2br"
  ],
  "replacements_path": "_course_metadata/_replacements/default.json"
}
```

#### 3.2 Templating with _style variants

Authors can standardize content and structure of all pages and assignments by:
- wrapping content with standard html markup (using `header.html` and `footer.html`)
- placing additional standardized content at the top and bottom of the page or assignment content (using `header.md` and `footer.md`).

```text
_course_metadata/
  _styles/
    general/
      header.html
      header.md
      footer.md
      footer.html
    custom/
      header.html
      header.md
      footer.md
      footer.html
```

For a selected variant (e.g. `general`), rendered page/assignment HTML is wrapped in this order:

```text
header.html → header.md → {page HTML} → footer.md → footer.html
```

This produces a consistent shell around all content by default while allowing variants via `style` in `defaults.json`.

This course-level template may be overridden on any page or assignment in the front matter of that `index.md` with an alternate style variant, for example an alternate style that can be stored anywhere `../../_course_metadata/_styles` or `_styles/custom`

```text
---
name: "Example Assignment"
type: "Assignment"
style: "../../_course_metadata/_styles/custom"
modules:
  - "Module 1: Getting Started"
published: true
---
```

#### 3.3 _replacements and `==mykey==` tokens
A simple replacement system lets you define common plain text elements or HTML snippets once, then reuse them everywhere. It can help authors to avoid repetitive editing and can update the element across an entire course just by changing a single definition.

When Zaphod process a page or assignment, it looks for a course-level default replacement file or one overridden specified in the page's frontmatter level

During translation, Zaphod replaces any `==course_code==`‑style tokens in rendered HTML using this mapping, as configured by `replacements_path`.

```text
_course_metadata/
  _replacements/
    default.json
```

Example `default.json`:

```json
{
  "==course_code==": "COURSE-101",
  "==support_email==": "support@example.edu"
}
```

In a similar way to `_styles`, `_replacements` can be overridden at the page level by specifying an alternate `replacements` file in the page or assignment's front matter. 

```text
---
name: "Example Assignment"
type: "Assignment"
style: "../../_course_metadata/_styles/custom"
replacements: "../../_course_metadata/_/replacements/custom_replacements.json"
modules:
  - "Module 1: Getting Started"
published: true
---
```

***

## 4. Environment and Canvas config

From `/path/to/courses/example-course`:

```bash
cd /path/to/courses/example-course
python -m venv .venv
source .venv/bin/activate
pip install markdown2canvas canvasapi watchdog python-frontmatter emoji markdown beautifulsoup4 lxml pyyaml
```

Canvas credentials:

```bash
mkdir -p /path/to/canvas_credentials
nano /path/to/canvas_credentials/credentials.txt
```

```python
API_KEY = "YOUR_CANVAS_API_TOKEN_HERE"
API_URL = "https://yourcanvas.institution.edu/"
```

Environment variables:

```bash
export CANVAS_CREDENTIAL_FILE=/path/to/canvas_credentials/credentials.txt
export COURSE_ID=123456
```

Scripts and `markdown2canvas` use these to connect to Canvas and the correct course.[1]

***

## 5. Core scripts

#### 5.1 frontmatter_to_meta.py

Walks `pages/` for `.page`, `.assignment`, etc., and for each folder:

- Parses `index.md` YAML frontmatter with `python-frontmatter`.[1]
- Writes `meta.json` and `source.md` if frontmatter has required keys.[1]
- Falls back to existing `meta.json`/`source.md` if frontmatter is missing or invalid.[1]

```python
#!/usr/bin/env python3
from pathlib import Path
import json
import frontmatter

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PAGES_DIR = REPO_ROOT / "pages"

def process_folder(folder: Path):
    index_path = folder / "index.md"
    meta_path = folder / "meta.json"
    source_path = folder / "source.md"

    has_index = index_path.is_file()
    has_meta = meta_path.is_file()
    has_source = source_path.is_file()

    # Preferred: YAML frontmatter in index.md
    if has_index:
        try:
            post = frontmatter.load(index_path)
        except Exception as e:
            print(f"[frontmatter:err] {index_path}: {e}")
        else:
            metadata = dict(post.metadata)
            content = post.content.strip() + "\n"

            for k in ["name", "type"]:
                if k not in metadata:
                    print(f"[frontmatter:warn] {index_path}: missing '{k}', falling back to meta.json")
                    break
            else:
                with meta_path.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                with source_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[✓ frontmatter] {folder.name}")
                return

    # Fallback: existing meta.json + source.md
    if has_meta and has_source:
        print(f"[↻ frontmatter:fallback] {folder.name}")
        return

    raise ValueError(
        f"No usable metadata for {folder}: "
        f"missing/invalid frontmatter and no meta.json/source.md."
    )

if __name__ == "__main__":
    if not PAGES_DIR.exists():
        raise SystemExit(f"No pages directory at {PAGES_DIR}")
    content_dirs = []
    for ext in [".page", ".assignment", ".link", ".file"]:
        content_dirs.extend(PAGES_DIR.rglob(f"*{ext}"))
    if not content_dirs:
        print("No content folders under pages/")
    for folder in content_dirs:
        process_folder(folder)
```

#### 5.2 publish_all.py

Uses `markdown2canvas` to publish all content folders to Canvas:

- Auto‑discovers `pages/**.page`, `pages/**.assignment`, etc.[1]
- Instantiates the right `markdown2canvas` object type and calls `.publish(course, overwrite=True)`.[1]
- Monkey‑patches `markdown2canvas`’s internal module logic to no‑op; modules are managed by `sync_modules.py`.[1]

```python
#!/usr/bin/env python3
import os
from pathlib import Path
import markdown2canvas as mc
from markdown2canvas import canvas_objects
from markdown2canvas.setup_functions import make_canvas_api_obj

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PAGES_DIR = REPO_ROOT / "pages"

# Disable buggy module handling inside markdown2canvas itself
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

canvas = make_canvas_api_obj()  # uses CANVAS_CREDENTIAL_FILE
COURSE_IDS = [int(os.environ.get("COURSE_ID", "0"))] if os.environ.get("COURSE_ID") else []

if __name__ == "__main__":
    if not COURSE_IDS:
        raise SystemExit("COURSE_ID is not set")
    for course_id in COURSE_IDS:
        course = canvas.get_course(course_id)
        print(f"Publishing to {course.name} (ID {course_id})")
        for d in content_dirs:
            try:
                obj = make_mc_obj(d)
                print(f"Processing: {d}")
                obj.publish(course, overwrite=True)
                print(f"[✓ publish] {d.name}")
            except Exception as e:
                print(f"[publish:err] {d.name}: {e}")
            print()
```

#### 5.3 sync_modules.py

- Reads `meta.json` for each `.page` folder.[1]
- Uses `canvasapi` to find or create modules and ensures each page appears in the listed modules (by title and `page_url`).[1]

```python
#!/usr/bin/env python3
from pathlib import Path
import json
import os
from canvasapi import Canvas

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PAGES_DIR = REPO_ROOT / "pages"

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
        raise FileNotFoundError(f"No meta.json in {folder}")
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
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")
    canvas = get_canvas()
    course = canvas.get_course(int(course_id))
    page_folders = list(PAGES_DIR.rglob("*.page"))
    print(f"Syncing modules in course {course.name} (ID {course_id})")
    for folder in page_folders:
        sync_page(course, folder)
        print()
```

***

## 6. Outcomes and rubrics

#### 6.1 sync_clo_via_csv.py (course outcomes via CSV)

- Reads `_course_metadata/outcomes.yaml`, expecting a `course_outcomes` list with fields like `code`, `title`, `description`, `vendor_guid`, `mastery_points`, and `ratings`.[1]
- Builds `_course_metadata/outcomes_import.csv` using Canvas’s Outcomes CSV schema, encoding rating levels as alternating `points,description` cells after a `ratings` header.[2]
- Calls `Course.import_outcome()` to import/update all course outcomes in one batch.[2]

```python
#!/usr/bin/env python3
"""
sync_clo_via_csv.py (Zaphod, CLOs with Canvas-style ratings)

For the current course (cwd):

- Reads _course_metadata/outcomes.yaml (course_outcomes)
- Generates _course_metadata/outcomes_import.csv using Canvas Outcomes CSV format,
  including rating levels as separate CSV cells after the `ratings` header
  (points,description,points,description,...).
- Imports that CSV into the course via Course.import_outcome().
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, Any, List

import yaml
from canvasapi import Canvas

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()
COURSE_META_DIR = COURSE_ROOT / "_course_metadata"
COURSE_OUTCOMES_YAML = COURSE_META_DIR / "outcomes.yaml"
COURSE_OUTCOMES_CSV = COURSE_META_DIR / "outcomes_import.csv"

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

    return Canvas(api_url, api_key)

def load_course_outcomes_yaml() -> Dict[str, Any]:
    if not COURSE_OUTCOMES_YAML.is_file():
        raise SystemExit(f"No outcomes.yaml at {COURSE_OUTCOMES_YAML}")
    with COURSE_OUTCOMES_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit("outcomes.yaml must be a mapping at top level")
    return data

def build_rows(course_clos: List[Dict[str, Any]]) -> List[List[str]]:
    """
    Build rows using the Outcomes CSV format with ratings encoded as separate cells
    after the ratings header.
    """
    rows: List[List[str]] = []

    for clo in course_clos:
        code = clo.get("code")
        title = clo.get("title")
        description = clo.get("description", "")
        vendor_guid = clo.get("vendor_guid") or code
        mastery_points = clo.get("mastery_points")
        ratings = clo.get("ratings") or []

        if not code or not title or not vendor_guid:
            print(f"[outcomes:warn] Skipping CLO with missing code/title/vendor_guid: {clo}")
            continue

        try:
            ratings_sorted = sorted(
                ratings,
                key=lambda r: float(r.get("points", 0)),
                reverse=True,
            )
        except Exception:
            ratings_sorted = ratings

        ratings_cells: List[str] = []
        for r in ratings_sorted:
            pts = r.get("points", "")
            desc = r.get("description", "")
            ratings_cells.append(str(pts))
            ratings_cells.append(desc)

        base = [
            str(vendor_guid),
            "outcome",
            title,
            description,
            code,           # display_name
            "",             # calculation_method
            "",             # calculation_int
            "active",       # workflow_state
            "",             # parent_guids
            str(mastery_points) if mastery_points is not None else "",
        ]

        row = base + ratings_cells
        rows.append(row)

    return rows

def write_csv(rows: List[List[str]]):
    COURSE_META_DIR.mkdir(parents=True, exist_ok=True)

    max_len = max((len(r) for r in rows), default=10)
    base_headers = [
        "vendor_guid",
        "object_type",
        "title",
        "description",
        "display_name",
        "calculation_method",
        "calculation_int",
        "workflow_state",
        "parent_guids",
        "mastery_points",
    ]
    extra_count = max(1, max_len - len(base_headers))
    extra_headers = ["ratings"] + [""] * (extra_count - 1)
    headers = base_headers + extra_headers

    with COURSE_OUTCOMES_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            padded = row[:]
            while len(padded) < len(headers):
                padded.append("")
            writer.writerow(padded)

    print(f"[outcomes] Wrote CSV with {len(rows)} outcomes to {COURSE_OUTCOMES_CSV}")

def import_csv_to_course(canvas: Canvas, course_id: int):
    """
    POST /api/v1/courses/:course_id/outcome_imports via Course.import_outcome().
    """
    course = canvas.get_course(course_id)
    print(f"[outcomes] Importing CSV into course {course_id}...")
    outcome_import = course.import_outcome(str(COURSE_OUTCOMES_CSV))
    attrs = getattr(outcome_import, "_attributes", {})
    print(
        f"[outcomes] Outcome import created: id={attrs.get('id')} "
        f"workflow_state={attrs.get('workflow_state')}"
    )

def main():
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")
    course_id_int = int(course_id)

    yaml_data = load_course_outcomes_yaml()
    course_clos: List[Dict[str, Any]] = yaml_data.get("course_outcomes") or []

    if not course_clos:
        print("[outcomes] No course_outcomes defined; nothing to do")
        return

    rows = build_rows(course_clos)
    if not rows:
        print("[outcomes] No valid CLO rows built; nothing written")
        return

    write_csv(rows)

    canvas = load_canvas()
    import_csv_to_course(canvas, course_id_int)

if __name__ == "__main__":
    main()
```

#### 6.2 sync_rubrics.py (assignment rubrics)

- Finds `rubric.yaml` / `rubric.yml` / `rubric.json` in each `.assignment` folder.[1]
- Uses `meta.json["name"]` to locate the Canvas assignment.[1]
- Builds rubric criteria from the spec, including outcome‑aligned criteria using `_course_metadata/outcome_map.json` (mapping outcome codes to Canvas outcome IDs).[3][2]
- Calls `Course.create_rubric()` with a rubric association to the assignment so it is used for grading.[2]

```python
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
    CANVAS_CREDENTIAL_FILE=/path/to/canvas_credentials/credentials.txt
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
from canvasapi import Canvas
from canvasapi.course import Course

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

    return Canvas(api_url, api_key)

def load_outcome_map() -> Dict[str, int]:
    """
    Load mapping from outcome_code -> outcome_id created by a separate outcomes sync step.
    """
    if not OUTCOME_MAP_PATH.is_file():
        print(f"[rubrics:warn] No outcome_map.json at {OUTCOME_MAP_PATH}; outcome-aligned rows will be skipped")
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
        raise FileNotFoundError(f"No meta.json in {folder}")
    with meta_path.open(encoding="utf-8") as f:
        return json.load(f)

def find_assignment_by_name(course: Course, name: str):
    """
    Find a Canvas assignment with a title matching 'name'.
    """
    for a in course.get_assignments():
        if a.name == name:
            return a
    return None

def build_rubric_params(
    rubric_spec: Dict[str, Any],
    outcome_map: Dict[str, int],
) -> Dict[str, Any]:
    """
    Build parameters for Course.create_rubric from rubric.yaml + outcome_map.
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

        key = str(idx)
        idx += 1

        crit_params: Dict[str, Any] = {
            "description": description,
            "long_description": long_description,
            "criterion_use_range": False,
        }

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
            code = crit.get("outcome_code")
            if not code:
                print(f"[rubrics:warn] outcome criterion '{cid}' missing outcome_code; treating as local")
            else:
                outcome_id = outcome_map.get(code)
                if not outcome_id:
                    print(f"[rubrics:warn] outcome_code '{code}' not found in outcome_map; treating '{cid}' as local")
                else:
                    crit_params["learning_outcome_id"] = int(outcome_id)
                    crit_params["mastery_points"] = crit.get("mastery_points", None)
                    crit_params["use_for_scoring"] = bool(crit.get("use_for_scoring", True))
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
    """
    rubric_params = build_rubric_params(rubric_spec, outcome_map)

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

    result = course.create_rubric(**merged)
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

    assignment = find_assignment_by_name(course, name)
    if not assignment:
        print(f"[rubrics:err] {folder.name}: assignment '{name}' not found in Canvas")
        return

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
    course = canvas.get_course(int(course_id))

    outcome_map = load_outcome_map()

    assignment_folders = iter_assignment_folders()
    if not assignment_folders:
        print(f"[rubrics] No *.assignment folders found under {PAGES_DIR}")
        return

    for folder in assignment_folders:
        process_assignment_folder(course, folder, outcome_map)
        print()

if __name__ == "__main__":
    main()
```

***

## 7. Quiz banks and Classic Quizzes

#### 7.1 Authoring quiz bank files with YAML frontmatter

Each quiz is defined in one `quiz-banks/*.quiz.txt` file. The file supports optional YAML frontmatter followed by a NYIT‑style text body.[2]

**Example file: `quiz-banks/week1.quiz.txt`**

```text
---
title: "Week 1 Reading Quiz"
points_per_question: 2          # default if not overridden
shuffle_answers: true
published: false
topics: ["TOPIC-ARG-1"]         # optional: course topics
outcomes: ["ILO-COMM-1"]        # optional: course/ILO codes
group: "Reading Checks"         # optional: later use Quiz Question Groups API
---

1. What is 2+3?

a) 6
b) 1
*c) 5
d) 10

2. Another multiple-choice question?

a) Option 1
*b) Option 2
c) Option 3
d) Option 4
```

**Frontmatter fields:**

- `title`: quiz title (fallback: filename stem).[4]
- `points_per_question`: default `points_possible` for parsed questions.[5]
- `shuffle_answers`: whether Canvas should shuffle answers.[6]
- `published`: whether to publish the quiz after creation.[6]
- `topics`: list of topic codes for later reporting/analytics (metadata only in current version).[2]
- `outcomes`: list of outcome codes for future outcome alignment layers (metadata only in current version).[2]
- `group`: future hook for creating question groups via the Quiz Question Groups API.[7]

**Body format (NYIT Canvas Exam Converter rules):**[5][2]

- Multiple choice: `a)` / `*c)` where `*` marks the correct option.
- Multiple answers: `[ ]` / `[*]` options.
- Short answer: `* answer` lines for acceptable answers.
- Essay: `####` marker to indicate essay question body.
- File upload: `^^^^` marker.
- True/False: `*a) True / b) False` or `a) True / *b) False`.

Questions are separated by blank lines; each starts with a numbered stem like `1. Question text`.

#### 7.2 sync_quiz_banks.py (NYIT → Classic Quizzes)

`shared/scripts/sync_quiz_banks.py` implements the quiz pipeline:[2]

- Scans `quiz-banks/` for `*.quiz.txt` files in the current course.[2]
- Splits each file into YAML frontmatter and body:
  - If the file starts with `---`, reads until the closing `---` and parses the block with `yaml.safe_load` into `quiz_meta`.[8][4]
  - The remainder of the file is passed unmodified to the NYIT parser.[2]
- Uses `quiz_meta` to:
  - Set quiz title, published state, shuffle answers, and optional time limit via `course.create_quiz()` (Classic Quiz endpoint).[4][6]
  - Provide a default `points_per_question` for each parsed question.[5]
  - Preserve `topics`, `outcomes`, and `group` for future reporting and question‑group support.[2]
- Parses the body using NYIT rules into a list of `ParsedQuestion` objects with type, stem, answers, and points.[2]
- For each question, builds a `question` payload and posts it via `POST /courses/:course_id/quizzes/:quiz_id/questions` (Quiz Questions API).[9][5]

```python
#!/usr/bin/env python3
"""
sync_quiz_banks.py (Zaphod v0.2+)

For the current course (cwd):

- Reads all *.quiz.txt files under quiz-banks/
- Optional YAML frontmatter at top (between --- lines) defines quiz metadata:
    ---
    title: "Week 1 Reading Quiz"
    points_per_question: 2
    shuffle_answers: true
    published: false
    topics: ["TOPIC-ARG-1"]
    outcomes: ["ILO-COMM-1"]
    ---

- Body uses NYIT Canvas Exam Converter text format:
    * Multiple choice: a) / *c) for correct
    * Multiple answers: [ ] / [*]
    * Short answer: * answer
    * Essay: ####
    * File-upload: ^^^^
    * True/False: *a) True / b) False

- Creates a Classic Quiz per file via /courses/:course_id/quizzes
- Adds each parsed question via Quiz Questions API /quizzes/:quiz_id/questions

Assumptions:
- Env:
    CANVAS_CREDENTIAL_FILE=/path/to/canvas_credentials/credentials.txt
    COURSE_ID=<canvas course id>
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import yaml  # pip install pyyaml
from canvasapi import Canvas

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSE_ROOT = Path.cwd()
QUIZ_BANKS_DIR = COURSE_ROOT / "quiz-banks"

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
        raise SystemExit(f"Credentials file must define API_KEY and API_URL. Missing: {e}")

    return Canvas(api_url, api_key)

def create_quiz(course, title: str, meta: Dict[str, Any]):
    """
    Create a Classic Quiz using metadata + sensible defaults.
    """
    description = meta.get("description", "")
    quiz_type = meta.get("quiz_type", "assignment")  # graded quiz
    published = bool(meta.get("published", False))
    shuffle_answers = bool(meta.get("shuffle_answers", True))
    time_limit = meta.get("time_limit")  # optional minutes

    quiz_params: Dict[str, Any] = {
        "title": title,
        "description": description,
        "quiz_type": quiz_type,
        "published": published,
        "shuffle_answers": shuffle_answers,
    }
    if time_limit is not None:
        quiz_params["time_limit"] = int(time_limit)

    quiz = course.create_quiz(quiz=quiz_params)
    print(f"[quiz] Created quiz '{quiz.title}' (id={quiz.id})")
    return quiz

def add_question(course_id: int, quiz, question_payload: Dict[str, Any], canvas: Canvas):
    """
    Add a single question to a Classic Quiz via Quiz Questions API.
    """
    path = f"courses/{course_id}/quizzes/{quiz.id}/questions"
    resp = canvas._Canvas__requester.request(
        "POST",
        f"/api/v1/{path}",
        _kwargs={"question": question_payload},
    )
    print(f"[quiz:q] added {question_payload.get('question_type')}: {question_payload.get('question_name')}")
    return resp

# ---------- Frontmatter handling ----------

def split_frontmatter_and_body(raw: str) -> Tuple[Dict[str, Any], str]:
    """
    If file starts with YAML frontmatter (--- ... ---), parse it.
    Otherwise return empty meta and whole text as body.
    """
    lines = raw.splitlines()
    if not lines or not lines[0].strip().startswith("---"):
        return {}, raw

    # find closing '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip().startswith("---"):
            end_idx = i
            break

    if end_idx is None:
        # malformed; treat as no frontmatter
        return {}, raw

    fm_text = "\n".join(lines[1:end_idx])
    body_text = "\n".join(lines[end_idx + 1 :])

    meta = yaml.safe_load(fm_text) or {}
    if not isinstance(meta, dict):
        meta = {}

    return meta, body_text

# ---------- Parsing NYIT quiz text ----------

@dataclass
class AnswerOption:
    text: str
    is_correct: bool = False

@dataclass
class ParsedQuestion:
    number: int
    stem: str
    qtype: str
    answers: List[AnswerOption] = field(default_factory=list)
    points: float = 1.0

QUESTION_HEADER_RE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")
MC_OPTION_RE = re.compile(r"^\s*([a-z])\)\s+(.*\S)\s*$")
MC_OPTION_CORRECT_RE = re.compile(r"^\s*\*([a-z])\)\s+(.*\S)\s*$")
MULTI_ANSWER_RE = re.compile(r"^\s*\[(\*|\s)\]\s*(.*\S)\s*$")
SHORT_ANSWER_RE = re.compile(r"^\s*\*\s+(.+\S)\s*$")
TF_TRUE_RE = re.compile(r"^\s*\*a\)\s*True\s*$", re.IGNORECASE)
TF_FALSE_RE = re.compile(r"^\s*\*b\)\s*False\s*$", re.IGNORECASE)

def split_questions(raw: str) -> List[List[str]]:
    """
    Split quiz text into question blocks, separated by single blank line(s).
    """
    lines = raw.splitlines()
    blocks: List[List[str]] = []
    cur: List[str] = []

    def push():
        nonlocal cur, blocks
        if cur and any(line.strip() for line in cur):
            blocks.append(cur)
        cur = []

    for line in lines:
        if not line.strip():
            push()
        else:
            cur.append(line)
    push()
    return blocks

def detect_qtype(block: List[str]) -> str:
    body = "\n".join(block)
    if "####" in body:
        return "essay"
    if "^^^^" in body:
        return "file_upload"

    for line in block:
        if MULTI_ANSWER_RE.match(line):
            return "multiple_answers"

    if any(SHORT_ANSWER_RE.match(line) for line in block):
        return "short_answer"

    has_true = any(re.search(r"a\)\s*True", line, re.IGNORECASE) for line in block)
    has_false = any(re.search(r"b\)\s*False", line, re.IGNORECASE) for line in block)
    if has_true and has_false:
        return "true_false"

    return "multiple_choice"

def parse_question_block(block: List[str], default_points: float) -> ParsedQuestion:
    if not block:
        raise ValueError("Empty question block")

    m = QUESTION_HEADER_RE.match(block[0])
    if not m:
        raise ValueError(f"Invalid question header: {block[0]!r}")
    number = int(m.group(1))
    stem_first_line = m.group(2).strip()
    rest = block[1:]

    qtype = detect_qtype(block)
    stem_lines: List[str] = [stem_first_line]
    answers: List[AnswerOption] = []

    if qtype == "multiple_choice":
        in_opts = False
        for line in rest:
            if MC_OPTION_CORRECT_RE.match(line) or MC_OPTION_RE.match(line):
                in_opts = True
                m_corr = MC_OPTION_CORRECT_RE.match(line)
                if m_corr:
                    _, text = m_corr.groups()
                    answers.append(AnswerOption(text=text.strip(), is_correct=True))
                else:
                    m_opt = MC_OPTION_RE.match(line)
                    if m_opt:
                        _, text = m_opt.groups()
                        answers.append(AnswerOption(text=text.strip(), is_correct=False))
            else:
                if not in_opts:
                    stem_lines.append(line)
        if not any(ans.is_correct for ans in answers):
            raise ValueError(f"Multiple-choice question {number} has no correct answer marked with *")
    elif qtype == "multiple_answers":
        in_opts = False
        for line in rest:
            mm = MULTI_ANSWER_RE.match(line)
            if mm:
                in_opts = True
                star, text = mm.groups()
                answers.append(AnswerOption(text=text.strip(), is_correct=(star == "*")))
            else:
                if not in_opts:
                    stem_lines.append(line)
        if not any(ans.is_correct for ans in answers):
            raise ValueError(f"Multiple-answers question {number} has no [*] options")
    elif qtype == "short_answer":
        for line in rest:
            m_sa = SHORT_ANSWER_RE.match(line)
            if m_sa:
                answers.append(AnswerOption(text=m_sa.group(1).strip(), is_correct=True))
            else:
                stem_lines.append(line)
        if not answers:
            raise ValueError(f"Short-answer question {number} has no '* answer' lines")
    elif qtype == "essay":
        for line in rest:
            if line.strip() == "####":
                continue
            stem_lines.append(line)
    elif qtype == "file_upload":
        for line in rest:
            if line.strip() == "^^^^":
                continue
            stem_lines.append(line)
    elif qtype == "true_false":
        correct_is_true: Optional[bool] = None
        for line in rest:
            if TF_TRUE_RE.match(line):
                correct_is_true = True
            elif TF_FALSE_RE.match(line):
                correct_is_true = False
            else:
                stem_lines.append(line)
        if correct_is_true is None:
            raise ValueError(f"True/False question {number} has no '*a) True' or '*b) False'")
        answers = [
            AnswerOption(text="True", is_correct=bool(correct_is_true)),
            AnswerOption(text="False", is_correct=not bool(correct_is_true)),
        ]
    else:
        raise ValueError(f"Unsupported question type: {qtype}")

    stem = "\n".join(line.strip() for line in stem_lines if line.strip())
    return ParsedQuestion(number=number, stem=stem, qtype=qtype, answers=answers, points=default_points)

def parse_quiz_text(raw: str, default_points: float) -> List[ParsedQuestion]:
    blocks = split_questions(raw)
    questions: List[ParsedQuestion] = []
    for block in blocks:
        try:
            q = parse_question_block(block, default_points=default_points)
            questions.append(q)
        except Exception as e:
            print(f"[quiz:err] Failed to parse question block: {e}")
    return questions

# ---------- Map parsed questions to Canvas payloads ----------

def to_canvas_question_payload(pq: ParsedQuestion) -> Dict[str, Any]:
    qtext_html = f"<p>{pq.stem}</p>"

    if pq.qtype == "multiple_choice":
        answers = []
        for i, ans in enumerate(pq.answers):
            answers.append(
                {
                    "answer_text": ans.text,
                    "answer_weight": 100 if ans.is_correct else 0,
                    "answer_position": i + 1,
                }
            )
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "multiple_choice_question",
            "points_possible": pq.points,
            "answers": answers,
        }

    if pq.qtype == "multiple_answers":
        correct_count = max(1, sum(1 for a in pq.answers if a.is_correct))
        per_correct = 100.0 / correct_count
        answers = []
        for i, ans in enumerate(pq.answers):
            weight = per_correct if ans.is_correct else 0.0
            answers.append(
                {
                    "answer_text": ans.text,
                    "answer_weight": weight,
                    "answer_position": i + 1,
                }
            )
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "multiple_answers_question",
            "points_possible": pq.points,
            "answers": answers,
        }

    if pq.qtype == "short_answer":
        answers = []
        for i, ans in enumerate(pq.answers):
            answers.append(
                {
                    "answer_text": ans.text,
                    "answer_weight": 100,
                    "answer_position": i + 1,
                }
            )
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "short_answer_question",
            "points_possible": pq.points,
            "answers": answers,
        }

    if pq.qtype == "essay":
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "essay_question",
            "points_possible": pq.points,
        }

    if pq.qtype == "file_upload":
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "file_upload_question",
            "points_possible": pq.points,
        }

    if pq.qtype == "true_false":
        answers = []
        for i, ans in enumerate(pq.answers):
            answers.append(
                {
                    "answer_text": ans.text,
                    "answer_weight": 100 if ans.is_correct else 0,
                    "answer_position": i + 1,
                }
            )
        return {
            "question_name": f"Q{pq.number}",
            "question_text": qtext_html,
            "question_type": "true_false_question",
            "points_possible": pq.points,
            "answers": answers,
        }

    raise ValueError(f"Unsupported question type for payload: {pq.qtype}")

# ---------- Main workflow ----------

def iter_quiz_files() -> List[Path]:
    if not QUIZ_BANKS_DIR.exists():
        return []
    return sorted(QUIZ_BANKS_DIR.glob("*.quiz.txt"))

def process_quiz_file(course, canvas: Canvas, path: Path, course_id: int):
    print(f"[quiz:file] {path.name}")
    raw = path.read_text(encoding="utf-8")

    meta, body = split_frontmatter_and_body(raw)
    default_points = float(meta.get("points_per_question", 1.0))

    questions = parse_quiz_text(body, default_points=default_points)
    if not questions:
        print(f"[quiz:warn] No questions parsed from {path.name}")
        return

    title = meta.get("title") or path.stem
    quiz = create_quiz(course, title=title, meta=meta)

    for pq in questions:
        payload = to_canvas_question_payload(pq)
        add_question(course_id, quiz, payload, canvas)

def main():
    course_id = os.environ.get("COURSE_ID")
    if not course_id:
        raise SystemExit("COURSE_ID is not set")

    canvas = load_canvas()
    course = canvas.get_course(int(course_id))

    quiz_files = iter_quiz_files()
    if not quiz_files:
        print(f"[quiz] No *.quiz.txt files under {QUIZ_BANKS_DIR}")
        return

    for path in quiz_files:
        process_quiz_file(course, canvas, path, int(course_id))
        print()

if __name__ == "__main__":
    main()
```

***

## 8. Watcher pipeline

#### 8.1 watch_and_publish.py

`watch_and_publish.py` monitors `pages/**/index.md` for changes and runs the Zaphod pipeline:[1]

1. `frontmatter_to_meta.py` – regenerate `meta.json` and `source.md`.  
2. `publish_all.py` – publish pages and assignments to Canvas.  
3. `sync_modules.py` – ensure pages are in the correct modules.  
4. `sync_clo_via_csv.py` – generate/import course outcomes from YAML.  
5. `sync_rubrics.py` – attach rubrics to assignments.  

Quizzes are synchronized by running:

```bash
python scripts/sync_quiz_banks.py
```

```python
#!/usr/bin/env python3
import time
import subprocess
from pathlib import Path
import os
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PAGES_DIR = REPO_ROOT / "pages"

DEBOUNCE_SECONDS = 1.0
last_run = 0.0
DOT_LINE = "." * 70

def fence(label: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(DOT_LINE)
    print(f"[{ts}] {label}\n")

class PublishOnChangeHandler(FileSystemEventHandler):
    def _maybe_run_pipeline(self):
        global last_run
        now = time.time()
        if now - last_run < DEBOUNCE_SECONDS:
            return
        last_run = now

        python_exe = REPO_ROOT / ".venv" / "bin" / "python"
        env = os.environ.copy()
        env["CANVAS_CREDENTIAL_FILE"] = "/path/to/canvas_credentials/credentials.txt"

        fence("CHANGE DETECTED → frontmatter_to_meta.py")
        subprocess.run(
            [str(python_exe), str(SCRIPT_DIR / "frontmatter_to_meta.py")],
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )

        fence("RUNNING: publish_all.py")
        subprocess.run(
            [str(python_exe), str(SCRIPT_DIR / "publish_all.py")],
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )

        fence("RUNNING: sync_modules.py")
        subprocess.run(
            [str(python_exe), str(SCRIPT_DIR / "sync_modules.py")],
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )

        fence("RUNNING: sync_clo_via_csv.py")
        subprocess.run(
            [str(python_exe), str(SCRIPT_DIR / "sync_clo_via_csv.py")],
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )

        fence("RUNNING: sync_rubrics.py")
        subprocess.run(
            [str(python_exe), str(SCRIPT_DIR / "sync_rubrics.py")],
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )

        fence("PIPELINE COMPLETE")

    def on_any_event(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        try:
            path.relative_to(PAGES_DIR)
        except ValueError:
            return

        if event.event_type not in ("modified", "created", "moved"):
            return

        if path.name != "index.md":
            return

        self._maybe_run_pipeline()

if __name__ == "__main__":
    fence(f"WATCHING: {PAGES_DIR} (index.md only)")
    event_handler = PublishOnChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(PAGES_DIR), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fence("WATCHER STOPPING")
        observer.stop()
    observer.join()
```

This keeps authoring simple: course pages and assignments are updated automatically on save, while quizzes are regenerated on demand from their `.quiz.txt` files.

***

## 9. Zaphod roadmap

Planned extensions:

1. **Institution and Program Level Outcomes (ILO/PLO)**  
   - Add shared outcome stores (e.g. `_institution/outcomes.yaml`, `_programs/<program>/outcomes.yaml`) that Zaphod courses can reference and reuse.  
   - Support hierarchical relationships between ILOs, PLOs, CLOs, and rubric rows.

2. **Course‑Level Topics and Tagging**  
   - Define a topics vocabulary (e.g. `_course_metadata/topics.yaml`).  
   - Allow `topics: [...]` in page, assignment, and quiz frontmatter to drive topic‑based reporting and coverage maps.

3. **Quiz Bank Enhancements**  
   - Integrate question groups using `group` metadata and the Quiz Question Groups API, enabling random draws from banks.
   - Add conversion utilities to export existing Canvas quizzes into NYIT‑style `.quiz.txt` format for offline editing and version control.

--- 
#### Credits
Zaphod is simply an extension of the supremely useful [markdown2canvas](https://github.com/ofloveandhate/markdown2canvas?tab=readme-ov-file) project by Silviana Amethyst which is [documented here](https://ofloveandhate.github.io/markdown2canvas/index.html). 

Zaphod uses the markdown(ish) plain text quiz building shorthand used in the awesome [CanvasExam Converter](https://site.nyit.edu/its/canvas_exam_converter)

Zaphod was built with the assistance of GPT-4o through [perplexity.ai](perplexity.ai)

Together, these move Zaphod toward a full curriculum‑level pipeline where outcomes, topics, content, quizzes, and rubrics live in a coherent, version‑controlled text representation synchronized to Canvas.
