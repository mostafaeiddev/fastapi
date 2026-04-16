from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os
import re

from Ex import (
    parse_activity_level,
    normalize_goal,
    load_dataset,
    get_phase,
    generate_plan_one_day,
    generate_plan_two_days,
    generate_plan_three_days,
    generate_plan_four_days,
    generate_plan_five_days,
    DATA_CSV
)

app = FastAPI()

# -------------------------
# Static files for images
# -------------------------
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "Images")
if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# -------------------------
# Load exercise metadata (Description + Image)
# -------------------------
XLSX_PATH = os.path.join(os.path.dirname(__file__), "all_workouts_final_with_descriptions3.xlsx")

def load_exercise_metadata() -> dict:
    """
    Returns dict: { "exercise_name_lower": { "description": ..., "image_url": ..., "video_url": ... } }
    """
    meta = {}
    if not os.path.exists(XLSX_PATH):
        return meta
    try:
        df = pd.read_excel(XLSX_PATH)
        for _, row in df.iterrows():
            name = str(row.get("Exercise_Name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in meta:
                continue  # keep first occurrence only
            meta[key] = {
                "description": str(row.get("Exercise_Description") or "").strip() or None,
                "image_url": _resolve_image_url(name),
                "video_url": str(row.get("URL Video") or "").strip() or None,
            }
    except Exception:
        pass
    return meta

def _normalize_for_image(name: str) -> str:
    """
    Normalize exercise name to match image filename pattern.
    e.g. "Barbell Bench Press" → tries "Barbell+Bench+Press.webp" and variants
    """
    # Replace spaces with + (as seen in the Images folder naming)
    return name.replace(" ", "+")

def _resolve_image_url(exercise_name: str) -> str | None:
    """
    Try to find a matching image file in the Images/ folder.
    Checks several naming patterns used in the folder.
    Returns relative URL like /images/Bench+Press.webp or None.
    """
    if not os.path.exists(IMAGES_DIR):
        return None

    # Build candidate filenames to try
    candidates = _build_image_candidates(exercise_name)

    for filename in candidates:
        full_path = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(full_path):
            return f"/images/{filename}"

    return None

def _build_image_candidates(name: str) -> list[str]:
    """
    Generate possible image filenames for a given exercise name.
    The Images folder uses .webp and .jpg/.png extensions with + or - separators.
    """
    candidates = []
    extensions = [".webp", ".jpg", ".jpeg", ".png"]

    # Pattern 1: "Barbell+Bench+Press"
    plus_name = name.replace(" ", "+")
    # Pattern 2: "Barbell Bench Press" (with spaces, rare but check)
    # Pattern 3: lowercase
    # Pattern 4: remove special chars

    for ext in extensions:
        candidates.append(f"{plus_name}{ext}")
        candidates.append(f"{plus_name.lower()}{ext}")

    # Pattern: words joined by nothing (CamelCase unlikely but worth checking)
    # Pattern: handle known aliases
    aliases = _get_known_aliases(name)
    for alias in aliases:
        for ext in extensions:
            candidates.append(f"{alias}{ext}")
            candidates.append(f"{alias.lower()}{ext}")

    return candidates

# Map exercise names that differ between xlsx and image filenames
EXERCISE_IMAGE_ALIASES = {
    "Barbell Bench Press": ["Machine+Bench+Press", "dumbbell-bench-press"],
    "Incline Barbell Press": ["incline-bench-press-benefits-types-technique"],
    "Dumbbell Bench Press": ["dumbbell-bench-press", "dumbbell-incline-bench-press"],
    "Incline Dumbbell Press": ["dumbbell-incline-bench-press", "Incline+Dumbbell+Curls"],
    "Cable Crossovers High to Low": ["cable-crossover-variation"],
    "Barbell Overhead Press": ["Barbell+Overhead+Press"],
    "Machine Shoulder Press": ["Machine+Shoulder+Press"],
    "Seated Rows Close-Grip": ["Seated+Rows+Close-Grip"],
    "Single-Arm Dumbbell Row": ["dumbbell-row"],
    "Romani Deadleft": ["Romani+Deadleft"],
    "Walking Lunges": ["Lunges"],
    "Dumbbell Lunges": ["Lunges"],
    "Standing Calf Raise": ["Standing+Calf+Raises"],
    "Close-Grip Bench Press": ["Close+Grip+Barbell+Bench+Press"],
    "Single-Arm Cable Pushdown": ["Rope+Pushdowns"],
    "Overhead Rope Extensions": ["Rope+Pushdowns"],
    "Cable Kickbacks": ["Dumbbell+Tricep+Kickback"],
    "Tricep Machine Dip": ["Dips"],
    "Lying Leg Raises": ["Leg+Raises"],
    "Toe Touches": ["Crunches"],
    "Cable Crunches": ["Crunches"],
    "Deadlifts": ["Romani+Deadleft"],
}

def _get_known_aliases(name: str) -> list[str]:
    return EXERCISE_IMAGE_ALIASES.get(name, [])

# Load metadata once at startup
EXERCISE_META: dict = load_exercise_metadata()

def enrich_exercise(exercise: dict) -> dict:
    """Add description and image_url to an exercise dict."""
    name = exercise.get("exercise_name", "")
    meta = EXERCISE_META.get(name.lower(), {})
    return {
        **exercise,
        "description": meta.get("description"),
        "image_url": meta.get("image_url"),
        "video_url": meta.get("video_url"),
    }

def enrich_plan(plan: dict) -> dict:
    """Walk the plan and enrich each exercise."""
    enriched = {}
    for day_key, day_val in plan.items():
        enriched_day = {**day_val}
        enriched_day["workout"] = [enrich_exercise(ex) for ex in day_val.get("workout", [])]
        enriched[day_key] = enriched_day
    return enriched

# -------------------------
# Request model
# -------------------------
class WorkoutRequest(BaseModel):
    userId: str
    #userName: str
    activityLevel: str
    goal: str
    availableDays: int

# -------------------------
# Main Endpoint
# -------------------------
@app.post("/generate-workout")
def generate_workout(req: WorkoutRequest):
    try:
        user_id = req.userId
       #user_name = req.userName
        activitylevel_raw = req.activityLevel
        goal_raw = req.goal
        available_days = req.availableDays

        # تحويل القيم
        level = parse_activity_level(activitylevel_raw)
        goal = normalize_goal(goal_raw)

        # تحميل الداتا
        dataset = load_dataset(DATA_CSV)
        week_index = 1
        phase = get_phase(week_index)
        detail = "compact"

        # توليد الخطة حسب عدد الأيام
        if available_days == 1:
            plan = generate_plan_one_day(user_id, user_name, level, dataset, week_index, phase, goal, detail)
        elif available_days == 2:
            plan = generate_plan_two_days(user_id, user_name, level, dataset, week_index, phase, goal, detail)
        elif available_days == 3:
            plan = generate_plan_three_days(user_id, user_name, level, dataset, week_index, phase, goal, detail)
        elif available_days == 4:
            plan = generate_plan_four_days(user_id, user_name, level, dataset, week_index, phase, goal, detail)
        elif available_days == 5:
            plan = generate_plan_five_days(user_id, user_name, level, dataset, week_index, phase, goal, detail)
        else:
            return {"status": "error", "message": "availableDays must be between 1 and 5"}

        plan = generators[req.availableDays]()
        plan = enrich_plan(plan)  # ← inject description + image_url + video_url

        return {
            "status": "ok",
            "user_id": user_id,
            "user_name": user_name,
            "fitness_level": level,
            "goal": goal,
            "available_days": req.availableDays,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "weeks": [
                {
                    "week_number": week_index,
                    "phase": phase,
                    "warmup": [
                        {"name": "Joint mobility", "duration": "5 min"},
                        {"name": "Light cardio", "duration": "5 min"},
                    ],
                    "days": plan,
                    "cooldown": [
                        {"name": "Static stretching", "duration": "5-8 min"},
                        {"name": "Breathing & relaxation", "duration": "2-3 min"},
                    ],
                    "notes": [
                        f"Phase: {phase}",
                        "Progressive overload: track weight and RPE; increase gradually.",
                    ],
                }
            ],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}