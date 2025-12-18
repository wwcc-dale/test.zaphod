#!/usr/bin/env python3
"""
watch_and_publish.py (Zaphod)

- Watches pages/**/index.md in the current course for changes.
- On any change, runs the full pipeline for that course:

    1) frontmatter_to_meta.py
    2) publish_all.py
    3) sync_modules.py
    4) sync_clo_via_csv.py   (manage CLOs via Outcomes CSV import)
    5) sync_rubrics.py
    6) sync_quiz_banks.py

Assumptions:
- You run this from a course root, e.g. ~/courses/test
- Shared layout: ~/courses/shared/.venv and ~/courses/shared/scripts
- Env:
    CANVAS_CREDENTIAL_FILE
    COURSE_ID
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime  # [web:1]
from pathlib import Path
from typing import List

from watchdog.events import PatternMatchingEventHandler  # [web:15]
from watchdog.observers import Observer  # [web:39]

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_ROOT = SCRIPT_DIR.parent
COURSES_ROOT = SHARED_ROOT.parent
COURSE_ROOT = Path.cwd()
PAGES_DIR = COURSE_ROOT / "pages"

DOT_LINE = "." * 70  # ~70-column visual separator

def fence(label: str):
    ts = datetime.now().strftime("%H:%M:%S")  # [web:1]
    print(DOT_LINE)
    print(f"[{ts}] {label}")
    print("\n")  # blank line after each phase

def run_pipeline():
    """
    Run the Zaphod pipeline for the current course.
    """
    python_exe = SHARED_ROOT / ".venv" / "bin" / "python"

    env = os.environ.copy()
    env.setdefault(
        "CANVAS_CREDENTIAL_FILE",
        str(Path.home() / ".canvas" / "credentials.txt"),
    )

    steps: List[Path] = [
        SCRIPT_DIR / "frontmatter_to_meta.py",
        SCRIPT_DIR / "publish_all.py",
        SCRIPT_DIR / "sync_modules.py",
        SCRIPT_DIR / "sync_clo_via_csv.py",
        SCRIPT_DIR / "sync_rubrics.py",
        SCRIPT_DIR / "sync_quiz_banks.py",
    ]

    fence("Zaphod pipeline start")
    for script in steps:
        if not script.is_file():
            print(f"[watch] SKIP missing script: {script}")
            continue
        fence(f"RUNNING: {script.name}")
        subprocess.run(
            [str(python_exe), str(script)],
            cwd=str(COURSE_ROOT),
            env=env,
            check=False,  # do not kill watcher on error [web:10]
        )
    fence("Zaphod pipeline complete")

class MarkdownChangeHandler(PatternMatchingEventHandler):
    def __init__(self):
        super().__init__(
            patterns=[
                "*/index.md",
                "*/*/index.md",
                "*/*/*/index.md",
                "outcomes.yaml",
            ],
            ignore_directories=False,
            case_sensitive=False,
        )

    def on_any_event(self, event):
        # Debounce noisy events by only reacting to file changes/creations.
        if event.is_directory:
            return
        if event.event_type not in {"modified", "created"}:
            return

        print(f"[watch] CHANGE DETECTED: {event.src_path}")
        run_pipeline()
        print("[watch] PIPELINE COMPLETE\n")

def main():
    if not PAGES_DIR.is_dir():
        raise SystemExit(f"pages/ directory not found under {COURSE_ROOT}")

    fence("WATCH")

    observer = Observer()
    handler = MarkdownChangeHandler()
    observer.schedule(handler, str(COURSE_ROOT), recursive=True)
    observer.start()

    print(f"[watch] WATCHING: {PAGES_DIR} (index.md only)")
    print(f"[watch] COURSE_ROOT: {COURSE_ROOT}\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
