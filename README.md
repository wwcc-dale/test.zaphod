# Zaphod
##### A version‑controlled, automatable course authoring environment that’s faster, safer, and more reusable than editing directly in Canvas.

Zaphod is a flat‑file Canvas course workflow where authors write course pages, assignments, quizzes, rubrics and outcomes and as structured text (markdown or yaml).

Each course can be placed under collaborative version control using Git. Python scripts translate and publish these text files to Canvas. In Canvas they become pages and assignments that may include rubrics associated with outcomes which can then be placed in modules. 

Quizzes in plain text shorthand (using NYIT‑style) become Classic quiz banks.

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

Required fields are `name` and `type`; `modules` and `published` are optional.

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

#### 3.3 _replacements and `{{mykey}}` tokens
A simple replacement system lets you define common plain text elements or HTML snippets once, then reuse them everywhere. It can help authors to avoid repetitive editing and can update the element across an entire course just by changing a single definition.

When Zaphod process a page or assignment, it looks for a course-level default replacement file or one overridden specified in the page's frontmatter level

During translation, Zaphod replaces any `{{course_code}}`‑style tokens in rendered HTML using this mapping, as configured by `replacements_path`.

```text
_course_metadata/
  _replacements/
    default.json
```

Example `default.json`:

```json
{
  "{{course_code}}": "COURSE-101",
  "{{support_email}}": "support@example.edu"
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

Scripts and `markdown2canvas` use these to connect to Canvas and the correct course.

***

## 5. Core scripts
- **Pages & Assignments**
    - `frontmatter_to_meta.py`
    - `publish_all.py`
    - `sync_modules.py`
- **Rubrics & Outcomes**
    - `sync_rubrics.py`
    - `generate_outcomes_csv.py`
    - `sync_clo_via_csv.py`
- **Quiz Banks**
    - `sync_quiz_banks.py`
- **Cleanup and Canvas Sync**
    - `prune_canvas_content.py`
    - `watch_and_publish.py`

### Pages & Assignments
#### ✔️ 5.1 frontmatter_to_meta.py

Walks `pages/` for `.page`, `.assignment`, etc., and for each folder:

- Parses `index.md` YAML frontmatter with `python-frontmatter`.
- Writes `meta.json` and `source.md` if frontmatter has required keys.
- Falls back to existing `meta.json`/`source.md` if frontmatter is missing or invalid.

#### ✔️ 5.2 publish_all.py

Uses `markdown2canvas` to publish all content folders to Canvas:

- Auto‑discovers `pages/**.page`, `pages/**.assignment`, etc.
- Instantiates the right `markdown2canvas` object type and calls `.publish(course, overwrite=True)`.
- Monkey‑patches `markdown2canvas`’s internal module logic to no‑op; modules are managed by `sync_modules.py`.

#### ✔️ 5.3 sync_modules.py

- Reads `meta.json` for each `.page` folder.
- Uses `canvasapi` to find or create modules and ensures each page appears in the listed modules (by title and `page_url`).

### Rubrics & Outcomes
#### ⚠️ 5.4 sync_rubrics.py (assignment rubrics)

- Finds `rubric.yaml` / `rubric.yml` / `rubric.json` in each `.assignment` folder.
- Uses `meta.json["name"]` to locate the Canvas assignment.
- Builds rubric criteria from the spec, including outcome‑aligned criteria using `_course_metadata/outcome_map.json` (mapping outcome codes to Canvas outcome IDs).
- Calls `Course.create_rubric()` with a rubric association to the assignment so it is used for grading.

#### ✔️ 5.5 generate_outcomes_csv.py

- Reads `_course_metadata/outcomes.yaml` and validates the `course_outcomes` structure.
- Generates `_course_metadata/outcomes_import.csv` in Canvas Outcomes CSV format without immediately importing it.
- Ensures:
  - Each outcome has a `code`, `title`, `vendor_guid`, and optional `mastery_points`.
  - Rating levels are sorted (typically by points, descending) and written as alternating `points,description` cells after the `ratings` header.

This script can be useful if you want to **preview or manually upload** the outcomes CSV via Canvas’s UI, or share it with admins, before running a fully automated import.

#### ✔️ 5.6 sync_clo_via_csv.py (course outcomes via CSV)

- Reads `_course_metadata/outcomes.yaml`, expecting a `course_outcomes` list with fields like `code`, `title`, `description`, `vendor_guid`, `mastery_points`, and `ratings`.
- Builds `_course_metadata/outcomes_import.csv` using Canvas’s Outcomes CSV schema, encoding rating levels as alternating `points,description` cells after a `ratings` header.
- Calls `Course.import_outcome()` to import/update all course outcomes in one batch.


#### ✔️ 5.7 sync_quiz_banks.py

Each quiz is defined in one `quiz-banks/*.quiz.txt` file. The file supports optional YAML frontmatter followed by a NYIT‑style text body.

**Example file: `quiz-banks/week1.quiz.txt`**

**Frontmatter fields:**

- `title`: quiz title (fallback: filename stem).
- `points_per_question`: default `points_possible` for parsed questions.
- `shuffle_answers`: whether Canvas should shuffle answers.
- `published`: whether to publish the quiz after creation.
- `topics`: list of topic codes for later reporting/analytics (metadata only in current version).
- `outcomes`: list of outcome codes for future outcome alignment layers (metadata only in current version).
- `group`: future hook for creating question groups via the Quiz Question Groups API.

**Body format (NYIT Canvas Exam Converter rules):**

- Multiple choice: `a)` / `*c)` where `*` marks the correct option.
- Multiple answers: `[ ]` / `[*]` options.
- Short answer: `* answer` lines for acceptable answers.
- Essay: `####` marker to indicate essay question body.
- File upload: `^^^^` marker.
- True/False: `*a) True / b) False` or `a) True / *b) False`.

Questions are separated by blank lines; each starts with a numbered stem like `1. Question text`.


`zaphod/scripts/sync_quiz_banks.py` implements the quiz pipeline:

- Scans `quiz-banks/` for `*.quiz.txt` files in the current course.
- Splits each file into YAML frontmatter and body:
  - If the file starts with `---`, reads until the closing `---` and parses the block with `yaml.safe_load` into `quiz_meta`.
  - The remainder of the file is passed unmodified to the NYIT parser.
- Uses `quiz_meta` to:
  - Set quiz title, published state, shuffle answers, and optional time limit via `course.create_quiz()` (Classic Quiz endpoint).
  - Provide a default `points_per_question` for each parsed question.
  - Preserve `topics`, `outcomes`, and `group` for future reporting and question‑group support.
- Parses the body using NYIT rules into a list of `ParsedQuestion` objects with type, stem, answers, and points.
- For each question, builds a `question` payload and posts it via `POST /courses/:course_id/quizzes/:quiz_id/questions` (Quiz Questions API).

🚧 **To do:** *Quiz banks successfully import questions, but the title value does not map to the bank name in Canvas. It appears as `Untitled Bank`. Users can rename the bank in Canvas, but this is something that should be fixed* 
### Cleanup & Canvas Sync
#### ✔️ 5.8 prune_canvas_content.py
- Compares **what exists in Canvas** (pages, assignments, quizzes, etc.) with the **local Zaphod repo**:
  - Local “truth”: everything under `pages/`, `quiz-banks/`, and other configured roots.
  - Canvas “work file” artifacts are removed after use
- Produces one or both of:
  - A **dry‑run report** listing candidate items to remove or unpublish.
  - Optional **cleanup actions**, such as unpublishing or deleting Canvas items that are no longer managed by Zaphod.

This keeps the Canvas course from accumulating stale or orphaned content as the flat‑file representation evolves.


#### ✔️ 5.9 watch_and_publish.py

Monitors the current course for file changes and automatically runs the full Zaphod pipeline whenever content of selected types are saved.

**What it watches:**

- `pages/**/index.md` (pages and assignments)
- `_course_metadata/outcomes.yaml` (course outcomes)
- `quiz-banks/*.quiz.txt` (quiz definitions)

**Pipeline steps (executed in order):**

1. `frontmatter_to_meta.py` – parse YAML frontmatter, generate `meta.json` and `source.md`
2. `publish_all.py` – publish pages and assignments to Canvas
3. `sync_modules.py` – ensure pages appear in the correct modules
4. `sync_clo_via_csv.py` – import/update course outcomes
5. `sync_rubrics.py` – attach rubrics to assignments
6. `sync_quiz_banks.py` – sync quiz banks to Canvas Classic Quizzes
7. `prune_canvas_content.py` – *(optional)* remove stale Canvas content not present in the repo


## 9. Zaphod Feature Roadmap

1. **Institution and Program Level Outcomes (ILO/PLO)**  
   - Add zaphod outcome stores (e.g. `_institution/outcomes.yaml`, `_programs/<program>/outcomes.yaml`) that Zaphod courses can reference and reuse.  
   - Support hierarchical relationships between ILOs, PLOs, CLOs, and rubric rows.

2. **Course‑Level Topics and Tagging**  
   - Define a topics vocabulary (e.g. `_course_metadata/topics.yaml`).  
   - Allow `topics: [...]` in page, assignment, and quiz frontmatter to drive topic‑based reporting and coverage maps.

3. **Quiz Bank Enhancements**  
   - Integrate question groups using `group` metadata and the Quiz Question Groups API, enabling random draws from banks.
--- 
#### Credits
Zaphod is simply an extension of the supremely useful [markdown2canvas](https://github.com/ofloveandhate/markdown2canvas?tab=readme-ov-file) project by Silviana Amethyst which is [documented here](https://ofloveandhate.github.io/markdown2canvas/index.html). 

Zaphod uses the markdown(ish) plain text quiz building shorthand used in the awesome [CanvasExam Converter](https://site.nyit.edu/its/canvas_exam_converter)

Zaphod was built with the assistance of GPT-4o through [perplexity.ai](perplexity.ai)

Together, these move Zaphod toward a full curriculum‑level pipeline where outcomes, topics, content, quizzes, and rubrics live in a coherent, version‑controlled text representation synchronized to Canvas.

---
&copy; 2005 Dale Chapman
