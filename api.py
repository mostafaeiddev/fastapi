from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os

DAY_IMAGE_MAP = {
    "Full Body":              "https://res.cloudinary.com/duprntyar/image/upload/v1776638094/full_body_tmqhb1.png",
    "Upper Body":             "https://res.cloudinary.com/duprntyar/image/upload/v1776638089/upper_body_umecey.png",
    "Lower Body":             "https://res.cloudinary.com/duprntyar/image/upload/v1776638085/lower_body_rhoyx6.png",
    "Push":                   "https://res.cloudinary.com/duprntyar/image/upload/v1776638086/push_day_n4vnk6.png",
    "Pull":                   "https://res.cloudinary.com/duprntyar/image/upload/v1776638086/pull_day_qojwe3.png",
    "Legs":                   "https://res.cloudinary.com/duprntyar/image/upload/v1776638095/leg_day_rjvyar.png",
    "Chest & Triceps":        "https://res.cloudinary.com/duprntyar/image/upload/v1776638092/chest_and_triceps_mupyaf.png",
    "Back & Biceps":          "https://res.cloudinary.com/duprntyar/image/upload/v1776638090/back_and_bicebs_nwj9qu.png",
    "Shoulders":              "https://res.cloudinary.com/duprntyar/image/upload/v1776638088/shoulder_on4d3y.png",
    "Chest":                  "https://res.cloudinary.com/duprntyar/image/upload/v1776638093/chest_a3lrka.png",
    "Back":                   "https://res.cloudinary.com/duprntyar/image/upload/v1776638091/back_wusfif.png",
    "Arms":                   "https://res.cloudinary.com/duprntyar/image/upload/v1776638090/back_and_bicebs_nwj9qu.png",
}


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
# Load Excel metadata
# -------------------------
BASE_DIR = os.path.dirname(__file__)
XLSX_PATH = os.path.join(BASE_DIR, "all_workouts_final_with_descriptions3.xlsx")




def load_exercise_metadata():
    meta = {}

    if not os.path.exists(XLSX_PATH):
        return meta

    df = pd.read_excel(XLSX_PATH)

    for _, row in df.iterrows():
        name = str(row.get("Exercise_Name") or "").strip()
        if not name:
            continue

        key = name.lower()

        meta[key] = {
            "description": str(row.get("Exercise_Description") or "").strip() or None,
            "image_url": str(row.get("URL Image") or "").strip() or None,  # ← بدل get_image_url
            "video_url": str(row.get("URL Video") or "").strip() or None,
        }

    return meta


EXERCISE_META = load_exercise_metadata()

EXERCISE_NAME_ALIASES = {
    "dumbbell lateral raises": "lateral raises",
    "barbell shrugs": "barbell rows",
    "dumbbell shrugs": "barbell rows",
    "deadlifts": "deadleft",
    "romani deadleft": "deadleft",
    "rear delt flyes": "face pulls",
    "traps": "barbell rows",
    "dumbbell concentration curls": "concentration curls",
    "dumbbell wrist curls": "dumbbell curls",
    "dumbbell reverse wrist curls": "dumbbell curls",
    "barbell curl": "barbell curls",
    "triceps pushdown": "tricep pushdown",
    "leg curl": "lying leg curl",
    "low cable rows": "seated rows close-grip",
    "hyperextensions": "barbell rows",
    "seated cable rows close-grip": "seated rows close-grip",
}
print("META COUNT:", len(EXERCISE_META))





def enrich_exercise(exercise: dict) -> dict:
    name = exercise.get("exercise_name", "")
    key = name.lower()
    key = EXERCISE_NAME_ALIASES.get(key, key)  # ← alias lookup
    meta = EXERCISE_META.get(key, {})

    return {
        **exercise,
        "description": meta.get("description"),
        "image_url": meta.get("image_url"),
        "video_url": meta.get("video_url"),
    }

def enrich_plan(plan: dict) -> dict:
    enriched = {}
    for day_key, day_val in plan.items():
        enriched_day = {
            "day_type": day_val.get("day_type"),
            "day_image_url": DAY_IMAGE_MAP.get(day_val.get("day_type"), None),
            "variations": day_val.get("variations"),
            "workout": [enrich_exercise(ex) for ex in day_val.get("workout", [])],
        }
        enriched[day_key] = enriched_day
    return enriched
# -------------------------
# Request model
# -------------------------
class WorkoutRequest(BaseModel):
    userId: str
    activityLevel: str
    goal: str
    availableDays: int


# -------------------------
# Endpoint
# -------------------------
@app.post("/generate-workout")
def generate_workout(req: WorkoutRequest):
    try:
        level = parse_activity_level(req.activityLevel)
        goal = normalize_goal(req.goal)

        dataset = load_dataset(DATA_CSV)

        week_index = 1
        phase = get_phase(week_index)

        # generate plan
        if req.availableDays == 1:
            plan = generate_plan_one_day(
                req.userId, level, dataset, week_index, phase, goal, "compact"
            )
        elif req.availableDays == 2:
            plan = generate_plan_two_days(
                req.userId, level, dataset, week_index, phase, goal, "compact"
            )
        elif req.availableDays == 3:
            plan = generate_plan_three_days(
                req.userId, level, dataset, week_index, phase, goal, "compact"
            )
        elif req.availableDays == 4:
            plan = generate_plan_four_days(
                req.userId, level, dataset, week_index, phase, goal, "compact"
            )
        elif req.availableDays == 5:
            plan = generate_plan_five_days(
                req.userId, level, dataset, week_index, phase, goal, "compact"
            )
        else:
            return {"status": "error", "message": "availableDays must be 1–5"}

        # enrich with images/videos/descriptions
        plan = enrich_plan(plan)

        return {
            "status": "ok",
            "user_id": req.userId,
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