import os
import json
from pathlib import Path

def get_course_id(course_dir=None):
    # First check environment variable
    course_id = os.environ.get("COURSE_ID")
    if course_id:
        return course_id
    
    # Fall back to defaults.json
    if course_dir is None:
        course_dir = Path.cwd()
    
    config_path = Path(course_dir) / "course_config" / "defaults.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            return config.get("course_id")
    
    return None

# Then use it:
course_id = get_course_id()
if not course_id:
    print("COURSE_ID is not set")
    sys.exit(1)
