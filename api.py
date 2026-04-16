from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os
import json

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
# Load Cloudinary URLs
# -------------------------
BASE_DIR = os.path.dirname(__file__)
CLOUDINARY_MAP_PATH = os.path.join(BASE_DIR, "cloudinary_urls.json")

def load_cloudinary_map():
    if not os.path.exists(CLOUDINARY_MAP_PATH):
        print("❌ cloudinary_urls.json not found")
        return {}

    with open(CLOUDINARY_MAP_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        item["public_id"].lower(): item["url"]
        for item in data
    }

CLOUDINARY_MAP = load_cloudinary_map()

# -------------------------
# Load Excel metadata
# -------------------------
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
        public_id = name.replace(" ", "+").lower()

        meta[key] = {
            "description": str(row.get("Exercise_Description") or "").strip() or None,
            "image_url": CLOUDINARY_MAP.get(public_id),
            "video_url": str(row.get("URL Video") or "").strip() or None,
        }

    return meta

EXERCISE_META = load_exercise_metadata()

print("META COUNT:", len(EXERCISE_META))

# -------------------------
# Enrich
# -------------------------
def enrich_exercise(exercise: dict) -> dict:
    name = exercise.get("exercise_name", "")
    meta = EXERCISE_META.get(name.lower(), {})

    return {
        **exercise,
        "description": meta.get("description"),
        "image_url": meta.get("image_url"),
        "video_url": meta.get("video_url"),
    }

def enrich_plan(plan: dict) -> dict:
    enriched = {}

    for day_key, day_val in plan.items():
        enriched_day = {**day_val}
        enriched_day["workout"] = [
            enrich_exercise(ex) for ex in day_val.get("workout", [])
        ]
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

        # generate
        if req.availableDays == 1:
            plan = generate_plan_one_day(req.userId, level, dataset, week_index, phase, goal, "compact")
        elif req.availableDays == 2:
            plan = generate_plan_two_days(req.userId, level, dataset, week_index, phase, goal, "compact")
        elif req.availableDays == 3:
            plan = generate_plan_three_days(req.userId, level, dataset, week_index, phase, goal, "compact")
        elif req.availableDays == 4:
            plan = generate_plan_four_days(req.userId, level, dataset, week_index, phase, goal, "compact")
        elif req.availableDays == 5:
            plan = generate_plan_five_days(req.userId, level, dataset, week_index, phase, goal, "compact")
        else:
            return {"status": "error", "message": "availableDays must be 1–5"}

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