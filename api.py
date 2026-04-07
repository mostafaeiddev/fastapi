from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

# استدعاء كل الدوال من Ex.py
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

        # إعدادات الأسبوع والمرحلة
        week_index = 1
        phase = get_phase(week_index)
        detail = "compact"

        # توليد الخطة حسب عدد الأيام
        if available_days == 1:
            plan = generate_plan_one_day(user_id, level, dataset, week_index, phase, goal, detail)
        elif available_days == 2:
            plan = generate_plan_two_days(user_id, level, dataset, week_index, phase, goal, detail)
        elif available_days == 3:
            plan = generate_plan_three_days(user_id,  level, dataset, week_index, phase, goal, detail)
        elif available_days == 4:
            plan = generate_plan_four_days(user_id,  level, dataset, week_index, phase, goal, detail)
        elif available_days == 5:
            plan = generate_plan_five_days(user_id,  level, dataset, week_index, phase, goal, detail)
        else:
            return {"status": "error", "message": "availableDays must be between 1 and 5"}

        # إخراج النتيجة
        output = {
            "status": "ok",
            "user_id": user_id,
            #"user_name": user_name,
            "fitness_level": level,
            "goal": goal,
            "available_days": available_days,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "weeks": [
                {
                    "week_number": week_index,
                    "phase": phase,
                    "warmup": [
                        {"name": "Joint mobility", "duration": "5 min"},
                        {"name": "Light cardio", "duration": "5 min"}
                    ],
                    "days": plan,
                    "cooldown": [
                        {"name": "Static stretching", "duration": "5-8 min"},
                        {"name": "Breathing & relaxation", "duration": "2-3 min"}
                    ],
                    "notes": [
                        f"Phase: {phase}",
                        "Progressive overload: track weight and RPE; increase gradually."
                    ]
                }
            ]
        }

        return output

    except Exception as e:
        return {"status": "error", "message": str(e)}