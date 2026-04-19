#!/usr/bin/env python3
# Ex.py

import sys
import os
import csv
import json
import random
import pandas as pd
from datetime import datetime


# -------------------------
# Config
# -------------------------
INCLUDE_CORE = False

# -------------------------
# Helpers
# -------------------------
def safe_print_json(obj):
    try:
        print(json.dumps(obj, ensure_ascii=False))
    except Exception:
        print(json.dumps({"status":"error","message":"Failed to serialize output"}))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def parse_activity_level(val):
    try:
        n = int(val)
        if n < 1: return "beginner"
        if n < 2: return "intermediate"
        return "advanced"
    except Exception:
        s = str(val).strip().lower()
        if s in ("beginner","b","1"): return "beginner"
        if s in ("intermediate","inter","2"): return "intermediate"
        return "advanced"

# -------------------------
# Paths
# -------------------------
DATA_CSV = os.path.join(os.path.dirname(__file__), "all_workouts_final_with_descriptions3.xlxs")
BRO_SPLIT_XLSX = os.path.join(os.path.dirname(__file__), "Bro_Split.xlsx")
PRO_SPLIT_XLSX = os.path.join(os.path.dirname(__file__), "pro_split.xlsx")
PRO_SPLIT_XLSX_ALT = os.path.join(os.path.dirname(__file__), "Pro_Split.xlsx")

# -------------------------
# Goal mapping
# -------------------------
GOAL_MAP = {
    "muscle_gain": ["muscle gain", "gain", "gain muscle", "gain muscles", "muscle", "muscles", "build muscle", "build_muscle", "mass", "bulking"],
    "fat_loss": ["fat loss", "lose weight", "lose", "cutting", "cut", "weight loss"],
    "strength": ["strength", "get_stronger", "strength gain", "power", "strength training"],
    "general": ["general", "maintain", "maintenance", "general fitness"]
}

def normalize_goal(raw):
    s = str(raw).strip().lower()
    for canonical, synonyms in GOAL_MAP.items():
        if s in synonyms:
            return canonical
    if "muscle" in s:
        return "muscle_gain"
    if "lose" in s or "fat" in s or "weight" in s:
        return "fat_loss"
    if "strength" in s:
        return "strength"
    return "general"

# -------------------------
# Load dataset (CSV) or fallback sample
# -------------------------
def load_dataset(path):
    exercises = []
    if os.path.exists(path):
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    ex = {
                        "Exercise_Name": r.get("Exercise_Name") or r.get("exercise_name") or "",
                        "Muscle_Group": r.get("Muscle_Group") or r.get("muscle_group") or "",
                        "Exercise_Type": r.get("Exercise_Type") or r.get("exercise_type") or "",
                        "Workout_Variation": r.get("Workout_Variation") or r.get("Workout_Variation") or "",
                        "Exercise_Number": int(r.get("Exercise_Number") or r.get("exercise_number") or 0),
                        "Primary_Equipment": r.get("Primary_Equipment") or r.get("primary_equipment") or ""
                    }
                    exercises.append(ex)
            if exercises:
                return exercises
        except Exception:
            pass

        sample = [
        {"Exercise_Name":"Barbell Bench Press","Muscle_Group":"Chest","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Incline Dumbbell Press","Muscle_Group":"Chest","Exercise_Type":"Compound","Workout_Variation":"Dumbbell","Exercise_Number":2,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Pec Deck Flyes","Muscle_Group":"Chest","Exercise_Type":"Isolation","Workout_Variation":"Machine","Exercise_Number":3,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Barbell Overhead Press","Muscle_Group":"Shoulders","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Lateral Raises","Muscle_Group":"Shoulders","Exercise_Type":"Isolation","Workout_Variation":"Dumbbell","Exercise_Number":2,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Rope Pushdowns","Muscle_Group":"Triceps","Exercise_Type":"Isolation","Workout_Variation":"Cable","Exercise_Number":1,"Primary_Equipment":"Cable"},
        {"Exercise_Name":"Lat Pulldowns","Muscle_Group":"Back","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Barbell Rows","Muscle_Group":"Back","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":2,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Barbell Curls","Muscle_Group":"Biceps","Exercise_Type":"Isolation","Workout_Variation":"Dumbbell","Exercise_Number":1,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Barbell Squats","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Leg Press","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Machine","Exercise_Number":2,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Lying Leg Curl","Muscle_Group":"Legs","Exercise_Type":"Isolation","Workout_Variation":"Machine","Exercise_Number":3,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Deadlifts","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":4,"Primary_Equipment":"Barbell"},
    ]
    return sample

# -------------------------
# Sets & reps logic
# -------------------------
BASE_SR = {
    "beginner": {
        "Compound": {"sets":3, "reps": (8,12)},
        "Isolation": {"sets":3, "reps": (10,15)}
    },
    "intermediate": {
        "Compound": {"sets":3, "reps": (6,10)},
        "Isolation": {"sets":3, "reps": (8,12)}
    },
    "advanced": {
        "Compound": {"sets":4, "reps": (4,8)},
        "Isolation": {"sets":4, "reps": (8,12)}
    }
}

def compute_sets_reps(level, ex_type, week_index=1, phase="Hypertrophy", goal="general"):
    sr = BASE_SR.get(level, BASE_SR["intermediate"]).get(ex_type, {"sets":3,"reps":(8,12)})
    sets = sr["sets"]
    min_rep, max_rep = sr["reps"]

    if phase == "Hypertrophy":
        min_rep += (week_index - 1)
        max_rep += (week_index - 1)
    elif phase == "Strength":
        min_rep = max(3, min_rep - 2)
        max_rep = max(5, max_rep - 2)
    elif phase == "Endurance":
        min_rep += 3
        max_rep += 3

    if goal == "fat_loss":
        min_rep += 2
        max_rep += 2
    elif goal == "strength":
        min_rep = max(3, min_rep - 1)
        max_rep = max(5, max_rep - 1)

    min_rep = clamp(int(min_rep), 1, 50)
    max_rep = clamp(int(max_rep), min_rep, 60)
    return sets, f"{min_rep}-{max_rep}"

def get_sets_reps(level, ex_type, week_index=1, phase="Hypertrophy", goal="general"):
    sets, reps = compute_sets_reps(level, ex_type, week_index, phase, goal)
    return {"sets": sets, "reps": reps}

def compute_rest_and_tempo(phase, goal):
    if phase == "Strength":
        rest = 120
        tempo = "1-0-3"
    elif phase == "Hypertrophy":
        rest = 60
        tempo = "2-0-2"
    else:
        rest = 45
        tempo = "2-0-1"
    if goal == "fat_loss":
        rest = max(20, rest - 15)
    return rest, tempo

def compute_rpe(week_index, phase):
    base = 7.0
    if phase == "Strength":
        base = 8.0
    elif phase == "Endurance":
        base = 6.5
    rpe = clamp(base + (week_index - 1) * 0.2, 5.0, 9.5)
    return round(rpe, 1)

# -------------------------
# Build day/week functions
# -------------------------
def choose_variation_no_repeat(group_list, used_variations):
    available = [v for v in group_list if v not in used_variations]
    if not available:
        available = group_list
    return random.choice(available) if available else None

def select_exercises_for_variation(ex_list, variation, used_names, max_per_group=3):
    candidates = [e for e in ex_list if e["Workout_Variation"] == variation]
    candidates = sorted(candidates, key=lambda x: x.get("Exercise_Number", 0))
    new_candidates = [c for c in candidates if c["Exercise_Name"] not in used_names]
    chosen = new_candidates[:max_per_group]
    if len(chosen) < max_per_group:
        remaining = [c for c in candidates if c not in chosen]
        chosen += remaining[:(max_per_group - len(chosen))]
    return chosen

def get_phase(week_index=1):
    phases = ["Hypertrophy", "Strength", "Endurance"]
    return phases[(week_index - 1) % len(phases)]

def build_day(muscle_groups, dataset, week_index, used_variations, used_ex_names, phase, level, goal, detail, full_day=False):
    day_exercises = []
    variations = {}

    for group in muscle_groups:
        group_items = [e for e in dataset if e["Muscle_Group"].lower() == group.lower()]
        if not group_items:
            continue

        variation_list = list({e["Workout_Variation"] for e in group_items})
        variation = random.choice(variation_list)
        variations[group] = variation
        filtered = [e for e in group_items if e["Workout_Variation"] == variation]

        if group in ["Chest", "Back", "Shoulders"]:
            selected = filtered
        elif group == "Biceps":
            selected = random.sample(filtered, min(3, len(filtered)))
        elif group == "Triceps":
            selected = random.sample(filtered, min(2, len(filtered)))
        elif group == "Legs":
            if full_day:
                compound_ex = [e for e in filtered if e.get("Exercise_Type","").lower() == "compound"]
                selected = random.sample(compound_ex, min(2, len(compound_ex)))
            else:
                selected = random.sample(filtered, min(7, len(filtered)))
        else:
            selected = random.sample(filtered, min(3, len(filtered)))

        for row in selected:
            sets, reps = compute_sets_reps(level, row.get("Exercise_Type", "Compound"), week_index, phase, goal)
            ex = {
                "exercise_name": row["Exercise_Name"],
                "muscle_group": row["Muscle_Group"],
                "exercise_type": row.get("Exercise_Type", "Compound"),
                "sets": sets,
                "reps": reps
            }
            day_exercises.append(ex)

    return {
        "variations": variations,
        "workout": day_exercises
    }

def add_core_and_accessory(day_plan, dataset, week_index, used_ex_names, phase, level, goal, detail):
    if not INCLUDE_CORE:
        return
    core_groups = ["Core","Abs","Accessory"]
    core_items = [e for e in dataset if e["Muscle_Group"] in core_groups]
    if not core_items:
        return
    chosen = random.sample(core_items, min(2, len(core_items)))
    for row in chosen:
        if row["Exercise_Name"] in used_ex_names:
            continue
        sets, reps = compute_sets_reps(level, row.get("Exercise_Type","Isolation"), week_index, phase, goal)
        rest, tempo = compute_rest_and_tempo(phase, goal)
        ex = {
            "exercise_name": row["Exercise_Name"],
            "muscle_group": row["Muscle_Group"],
            "exercise_type": row.get("Exercise_Type","Isolation"),
            "sets": sets,
            "reps": reps
        }
        if detail == "full":
            ex.update({"tempo": tempo, "rest_seconds": rest, "rpe": compute_rpe(week_index, phase)})
        elif detail == "compact":
            ex.update({"tempo": tempo})
        day_plan["workout"].append(ex)
        used_ex_names.add(row["Exercise_Name"])

def _collect_and_fill_variation(df_group, chosen_variation, min_needed=4):
    if df_group.empty:
        return []

    primary = df_group[df_group['Workout_Variation'] == chosen_variation].sort_values('Exercise_Number')
    collected = list(primary.to_dict(orient='records'))

    if len(collected) >= min_needed:
        return collected

    other = df_group[df_group['Workout_Variation'] != chosen_variation].sort_values('Exercise_Number')
    for _, row in other.iterrows():
        name = row.get('Exercise_Name') or row.get('exercise_name')
        if any((r.get('Exercise_Name') == name) or (r.get('exercise_name') == name) for r in collected):
            continue
        collected.append(row.to_dict())
        if len(collected) >= min_needed:
            break

    return collected

def _load_csv_df(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def _load_shoulder_excel():
    excel_paths = [
        os.path.join(os.path.dirname(__file__), "Bro_Split.xlsx"),
        os.path.join(os.path.dirname(__file__), "pro_split.xlsx"),
        os.path.join(os.path.dirname(__file__), "Pro_Split.xlsx")
    ]
    for path in excel_paths:
        if os.path.exists(path):
            try:
                return pd.read_excel(path)
            except Exception:
                continue
    return pd.DataFrame()

# -------------------------
# Helper: fill exercises to min count from other variations
# -------------------------
def _fill_to_min(df_source, chosen_variation, exercises, used_names, user_fitness_level, min_count=5):
    """Fill exercises list to min_count by pulling from other variations."""
    if len(exercises) >= min_count:
        return exercises

    other = df_source[df_source['Workout_Variation'] != chosen_variation].sort_values('Exercise_Number')
    for _, row in other.iterrows():
        if len(exercises) >= min_count:
            break
        ex_name = row.get('Exercise_Name', '')
        if not ex_name or ex_name in used_names:
            continue
        ex_type = row.get('Exercise_Type', 'Compound')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": row.get('Muscle_Group', ''),
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
        used_names.add(ex_name)

    return exercises

# -------------------------
# 5-Day plan generators
# -------------------------
def generate_workout_chest_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    chest_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        chest_df = df_excel[df_excel['Muscle_Group'] == 'Chest']
    if chest_df.empty:
        chest_df = df_csv[df_csv['Muscle_Group'] == 'Chest']

    variation_Chest = random.choice(list(chest_df['Workout_Variation'].unique())) if not chest_df.empty else None

    exercises = []
    used_names = set()

    if variation_Chest:
        primary = chest_df[chest_df['Workout_Variation'] == variation_Chest].sort_values('Exercise_Number')
        for _, row in primary.iterrows():
            ex_type = row.get('Exercise_Type', 'Compound')
            ex_name = row.get('Exercise_Name', '')
            sr = get_sets_reps(user_fitness_level, ex_type)
            exercises.append({
                "exercise_name": ex_name,
                "muscle_group": row.get('Muscle_Group', 'Chest'),
                "exercise_type": ex_type,
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names.add(ex_name)

    # Fill to minimum 5
    exercises = _fill_to_min(chest_df, variation_Chest, exercises, used_names, user_fitness_level, min_count=5)

    return {"variations": {"Chest": variation_Chest}, "workout": exercises}


def generate_workout_back_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    back_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        back_df = df_excel[df_excel['Muscle_Group'] == 'Back']
    if back_df.empty:
        back_df = df_csv[df_csv['Muscle_Group'] == 'Back']

    variation_Back = random.choice(list(back_df['Workout_Variation'].unique())) if not back_df.empty else None

    exercises = []
    used_names = set()

    if variation_Back:
        primary = back_df[back_df['Workout_Variation'] == variation_Back].sort_values('Exercise_Number')
        for _, row in primary.iterrows():
            ex_type = row.get('Exercise_Type', 'Compound')
            ex_name = row.get('Exercise_Name', '')
            sr = get_sets_reps(user_fitness_level, ex_type)
            exercises.append({
                "exercise_name": ex_name,
                "muscle_group": row.get('Muscle_Group', 'Back'),
                "exercise_type": ex_type,
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names.add(ex_name)

    # Fill to minimum 5
    exercises = _fill_to_min(back_df, variation_Back, exercises, used_names, user_fitness_level, min_count=5)

    return {"variations": {"Back": variation_Back}, "workout": exercises}


def generate_workout_leg_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    legs_df = pd.DataFrame()
    if df_excel is not None and not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        legs_df = df_excel[df_excel['Muscle_Group'] == 'Legs']
    if legs_df.empty:
        if df_csv is not None and not df_csv.empty:
            legs_df = df_csv[df_csv['Muscle_Group'] == 'Legs']

    variation_Legs = None
    if not legs_df.empty and 'Workout_Variation' in legs_df.columns:
        unique_variations = legs_df['Workout_Variation'].unique()
        if len(unique_variations) > 0:
            variation_Legs = random.choice(list(unique_variations))

    exercises = []

    if variation_Legs and not legs_df.empty:
        workout_df = legs_df[legs_df['Workout_Variation'] == variation_Legs].sort_values('Exercise_Number')
        for _, row in workout_df.iterrows():
            ex_type = row.get('Exercise_Type', 'Compound')
            if pd.isna(ex_type):
                ex_type = 'Compound'
            sr = get_sets_reps(user_fitness_level, ex_type)
            exercises.append({
                "exercise_name": row.get('Exercise_Name', 'Unknown'),
                "muscle_group": row.get('Muscle_Group', 'Legs'),
                "exercise_type": ex_type,
                "sets": sr["sets"],
                "reps": sr["reps"]
            })

    # Always include Deadlifts
    sr = get_sets_reps(user_fitness_level, "Compound")
    exercises.append({
        "exercise_name": "Deadlifts",
        "muscle_group": "Legs",
        "exercise_type": "Compound",
        "sets": sr["sets"],
        "reps": sr["reps"]
    })

    return {"variations": {"Legs": variation_Legs}, "workout": exercises}


def generate_workout_shoulder_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    shoulder_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        shoulder_df = df_excel[df_excel['Muscle_Group'] == 'Shoulders']
    if shoulder_df.empty:
        shoulder_df = df_csv[df_csv['Muscle_Group'] == 'Shoulders']

    variation = random.choice(list(shoulder_df['Workout_Variation'].unique())) if not shoulder_df.empty else None

    exercises = []
    used_names = set()

    if variation:
        primary = shoulder_df[shoulder_df['Workout_Variation'] == variation].sort_values('Exercise_Number')
        for _, row in primary.iterrows():
            ex_type = row.get('Exercise_Type', 'Isolation')
            ex_name = row.get('Exercise_Name', '')
            sr = get_sets_reps(user_fitness_level, ex_type)
            exercises.append({
                "exercise_name": ex_name,
                "muscle_group": row.get('Muscle_Group', 'Shoulders'),
                "exercise_type": ex_type,
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names.add(ex_name)

    # Fill to minimum 5
    exercises = _fill_to_min(shoulder_df, variation, exercises, used_names, user_fitness_level, min_count=5)

    return {"variations": {"Shoulders": variation}, "workout": exercises}


def generate_workout_arms_day_df(df_excel, user_fitness_level="beginner"):
    if df_excel.empty or 'Muscle_Group' not in df_excel.columns:
        return {"variations": {}, "workout": []}

    arms_df = df_excel[df_excel['Muscle_Group'].str.lower() == 'arms']
    if arms_df.empty:
        return {"variations": {}, "workout": []}

    arms_variation = random.choice(arms_df['Workout_Variation'].unique())

    exercises = []
    used_names = set()

    primary = arms_df[arms_df['Workout_Variation'] == arms_variation].sort_values('Exercise_Number')
    for _, row in primary.iterrows():
        ex_type = row.get('Exercise_Type', 'Isolation')
        ex_name = row.get('Exercise_Name', '')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": row.get('Muscle_Group', 'Arms'),
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
        used_names.add(ex_name)

    # Fill to minimum 5
    exercises = _fill_to_min(arms_df, arms_variation, exercises, used_names, user_fitness_level, min_count=6)

    return {"variations": {"Arms": arms_variation}, "workout": exercises}


def generate_workout_push_day(df, user_fitness_level="beginner"):
    Chest_df = df[df['Muscle_Group'] == 'Chest']
    Shoulder_df = df[df['Muscle_Group'] == 'Shoulders']
    Triceps_df = df[df['Muscle_Group'] == 'Triceps']

    variation_Chest = random.choice(list(Chest_df['Workout_Variation'].unique())) if not Chest_df.empty else None
    variation_Shoulder = random.choice(list(Shoulder_df['Workout_Variation'].unique())) if not Shoulder_df.empty else None
    variation_Triceps = random.choice(list(Triceps_df['Workout_Variation'].unique())) if not Triceps_df.empty else None

    parts = []
    if variation_Chest:
        parts.append(Chest_df[Chest_df['Workout_Variation'] == variation_Chest].sort_values('Exercise_Number'))
    if variation_Shoulder:
        parts.append(Shoulder_df[Shoulder_df['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number'))
    if variation_Triceps:
        parts.append(Triceps_df[Triceps_df['Workout_Variation'] == variation_Triceps].sort_values('Exercise_Number'))

    workout_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=df.columns)

    exercises = []
    for _, row in workout_df.iterrows():
        sets_reps = get_sets_reps(user_fitness_level, row['Exercise_Type'])
        exercises.append({
            "exercise_name": row['Exercise_Name'],
            "muscle_group": row['Muscle_Group'],
            "exercise_type": row['Exercise_Type'],
            "sets": sets_reps["sets"],
            "reps": sets_reps["reps"]
        })

    return {"variations": {"Chest": variation_Chest, "Shoulder": variation_Shoulder, "Triceps": variation_Triceps}, "workout": exercises}


def generate_workout_pull_day(df, user_fitness_level="beginner"):
    Back_df = df[df['Muscle_Group'] == 'Back']
    Biceps_df = df[df['Muscle_Group'] == 'Biceps']

    rear_delts_exercises = ['Face Pulls', 'Rear Delt Flyes']

    variation_Back = random.choice(list(Back_df['Workout_Variation'].unique())) if not Back_df.empty else None
    variation_Biceps = random.choice(list(Biceps_df['Workout_Variation'].unique())) if not Biceps_df.empty else None

    parts = []
    if variation_Back:
        parts.append(Back_df[Back_df['Workout_Variation'] == variation_Back])
    if variation_Biceps:
        parts.append(Biceps_df[Biceps_df['Workout_Variation'] == variation_Biceps])

    workout_df = pd.concat(parts).sort_values('Exercise_Number') if parts else pd.DataFrame(columns=df.columns)

    exercises = []
    for _, row in workout_df.iterrows():
        sets_reps = get_sets_reps(user_fitness_level, row['Exercise_Type'])
        exercises.append({
            "exercise_name": row['Exercise_Name'],
            "muscle_group": row['Muscle_Group'],
            "exercise_type": row['Exercise_Type'],
            "sets": sets_reps["sets"],
            "reps": sets_reps["reps"]
        })

    for ex in rear_delts_exercises:
        sr = get_sets_reps(user_fitness_level, "Isolation")
        exercises.append({
            "exercise_name": ex,
            "muscle_group": "Rear Delts",
            "exercise_type": "Isolation",
            "sets": sr["sets"],
            "reps": sr["reps"]
        })

    sr = get_sets_reps(user_fitness_level, "Compound")
    exercises.append({
        "exercise_name": "Traps",
        "muscle_group": "Traps",
        "exercise_type": "Compound",
        "sets": sr["sets"],
        "reps": sr["reps"]
    })

    return {"variations": {"Back": variation_Back, "Biceps": variation_Biceps}, "workout": exercises}


# -------------------------
# Plan generators
# -------------------------
def generate_plan_one_day(user_id, level, dataset, week_index, phase, goal, detail):
    day = build_day(["Chest","Back","Legs","Shoulders","Biceps","Triceps"],
                    dataset, week_index, set(), set(), phase, level, goal, detail, full_day=True)
    add_core_and_accessory(day, dataset, week_index, set(), phase, level, goal, detail)
    return {"day1": {"day_type":"Full Body", **day}}


def generate_plan_two_days(user_id, level, dataset, week_index, phase, goal, detail):
    upper_groups = ["Chest","Back","Shoulders","Biceps","Triceps"]
    d1 = build_day(upper_groups, dataset, week_index, set(), set(), phase, level, goal, detail, full_day=False)
    add_core_and_accessory(d1, dataset, week_index, set(), phase, level, goal, detail)
    d2 = build_day(["Legs"], dataset, week_index, set(), set(), phase, level, goal, detail, full_day=False)
    add_core_and_accessory(d2, dataset, week_index, set(), phase, level, goal, detail)
    return {"day1": {"day_type":"Upper Body", **d1}, "day2": {"day_type":"Lower Body", **d2}}


def generate_plan_three_days(user_id, level, dataset, week_index, phase, goal, detail):
    df = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()
    user_level = level

    push = generate_workout_push_day(df, user_fitness_level=user_level)
    pull = generate_workout_pull_day(df, user_fitness_level=user_level)
    legs = generate_workout_leg_day_df(df, df_excel, user_fitness_level=user_level)

    if INCLUDE_CORE:
        d1 = {"variations": push.get("variations", {}), "workout": push.get("workout", [])}
        add_core_and_accessory(d1, dataset, week_index, set(), phase, level, goal, detail)
        push["workout"] = d1["workout"]

        d2 = {"variations": pull.get("variations", {}), "workout": pull.get("workout", [])}
        add_core_and_accessory(d2, dataset, week_index, set(), phase, level, goal, detail)
        pull["workout"] = d2["workout"]

        d3 = {"variations": legs.get("variations", {}), "workout": legs.get("workout", [])}
        add_core_and_accessory(d3, dataset, week_index, set(), phase, level, goal, detail)
        legs["workout"] = d3["workout"]

    return {
        "day1": {"day_type": "Push", **push},
        "day2": {"day_type": "Pull", **pull},
        "day3": {"day_type": "Legs", **legs}
    }


def generate_plan_four_days(user_id, level, dataset, week_index, phase, goal, detail):
    df_csv = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()

    # ==================== DAY 1: CHEST + TRICEPS ====================
    Chest_df = df_csv[df_csv['Muscle_Group'] == 'Chest']
    Triceps_df = df_csv[df_csv['Muscle_Group'] == 'Triceps']

    variation_Chest = random.choice(Chest_df['Workout_Variation'].unique()) if not Chest_df.empty else None
    variation_Triceps = random.choice(Triceps_df['Workout_Variation'].unique()) if not Triceps_df.empty else None

    day1_exercises = []
    used_names_day1 = set()

    if variation_Chest:
        chest_exercises = Chest_df[Chest_df['Workout_Variation'] == variation_Chest].sort_values('Exercise_Number')
        for _, row in chest_exercises.iterrows():
            sr = get_sets_reps(level, row['Exercise_Type'])
            day1_exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names_day1.add(row['Exercise_Name'])

    if variation_Triceps:
        triceps_exercises = Triceps_df[Triceps_df['Workout_Variation'] == variation_Triceps].sort_values('Exercise_Number')
        for _, row in triceps_exercises.iterrows():
            sr = get_sets_reps(level, row['Exercise_Type'])
            day1_exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names_day1.add(row['Exercise_Name'])

    # Fill Chest to min 5 if needed (fill from Chest other variations)
    if len([e for e in day1_exercises if e['muscle_group'] == 'Chest']) < 5:
        chest_used = {e['exercise_name'] for e in day1_exercises if e['muscle_group'] == 'Chest'}
        other_chest = Chest_df[Chest_df['Workout_Variation'] != variation_Chest].sort_values('Exercise_Number')
        for _, row in other_chest.iterrows():
            if len([e for e in day1_exercises if e['muscle_group'] == 'Chest']) >= 5:
                break
            ex_name = row['Exercise_Name']
            if ex_name in chest_used:
                continue
            sr = get_sets_reps(level, row['Exercise_Type'])
            day1_exercises.append({
                "exercise_name": ex_name,
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            chest_used.add(ex_name)

    day1 = {
        "variations": {"Chest": variation_Chest, "Triceps": variation_Triceps},
        "workout": day1_exercises
    }

    # ==================== DAY 2: BACK + BICEPS ====================
    Back_df = df_csv[df_csv['Muscle_Group'] == 'Back']
    Biceps_df = df_csv[df_csv['Muscle_Group'] == 'Biceps']

    variation_Back = random.choice(Back_df['Workout_Variation'].unique()) if not Back_df.empty else None
    variation_Biceps = random.choice(Biceps_df['Workout_Variation'].unique()) if not Biceps_df.empty else None

    day2_exercises = []
    used_names_day2 = set()

    if variation_Back:
        back_exercises = Back_df[Back_df['Workout_Variation'] == variation_Back].sort_values('Exercise_Number')
        for _, row in back_exercises.iterrows():
            sr = get_sets_reps(level, row['Exercise_Type'])
            day2_exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names_day2.add(row['Exercise_Name'])

    if variation_Biceps:
        biceps_exercises = Biceps_df[Biceps_df['Workout_Variation'] == variation_Biceps].sort_values('Exercise_Number')
        for _, row in biceps_exercises.iterrows():
            sr = get_sets_reps(level, row['Exercise_Type'])
            day2_exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names_day2.add(row['Exercise_Name'])

    # Fill Back to min 5 if needed
    if len([e for e in day2_exercises if e['muscle_group'] == 'Back']) < 5:
        back_used = {e['exercise_name'] for e in day2_exercises if e['muscle_group'] == 'Back'}
        other_back = Back_df[Back_df['Workout_Variation'] != variation_Back].sort_values('Exercise_Number')
        for _, row in other_back.iterrows():
            if len([e for e in day2_exercises if e['muscle_group'] == 'Back']) >= 5:
                break
            ex_name = row['Exercise_Name']
            if ex_name in back_used:
                continue
            sr = get_sets_reps(level, row['Exercise_Type'])
            day2_exercises.append({
                "exercise_name": ex_name,
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            back_used.add(ex_name)

    day2 = {
        "variations": {"Back": variation_Back, "Biceps": variation_Biceps},
        "workout": day2_exercises
    }

    # ==================== DAY 3: SHOULDERS ====================
    day3_exercises = []
    used_names_day3 = set()
    variation_Shoulder = None
    shoulder_df_used = pd.DataFrame()

    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        shoulder_df = df_excel[df_excel['Muscle_Group'] == 'Shoulders']
        if not shoulder_df.empty:
            variation_Shoulder = random.choice(shoulder_df['Workout_Variation'].unique())
            shoulder_df_used = shoulder_df
            shoulder_exercises = shoulder_df[shoulder_df['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number')
            for _, row in shoulder_exercises.iterrows():
                sr = get_sets_reps(level, row.get('Exercise_Type', 'Isolation'))
                ex_name = row.get('Exercise_Name', '')
                day3_exercises.append({
                    "exercise_name": ex_name,
                    "muscle_group": row.get('Muscle_Group', 'Shoulders'),
                    "exercise_type": row.get('Exercise_Type', 'Isolation'),
                    "sets": sr["sets"],
                    "reps": sr["reps"]
                })
                used_names_day3.add(ex_name)

    if not day3_exercises:
        shoulder_df_csv = df_csv[df_csv['Muscle_Group'] == 'Shoulders']
        if not shoulder_df_csv.empty:
            variation_Shoulder = random.choice(shoulder_df_csv['Workout_Variation'].unique())
            shoulder_df_used = shoulder_df_csv
            shoulder_exercises = shoulder_df_csv[shoulder_df_csv['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number')
            for _, row in shoulder_exercises.iterrows():
                sr = get_sets_reps(level, row['Exercise_Type'])
                ex_name = row['Exercise_Name']
                day3_exercises.append({
                    "exercise_name": ex_name,
                    "muscle_group": row['Muscle_Group'],
                    "exercise_type": row['Exercise_Type'],
                    "sets": sr["sets"],
                    "reps": sr["reps"]
                })
                used_names_day3.add(ex_name)

    # Fill Shoulders to min 5
    day3_exercises = _fill_to_min(shoulder_df_used, variation_Shoulder, day3_exercises, used_names_day3, level, min_count=5)

    day3 = {
        "variations": {"Shoulders": variation_Shoulder},
        "workout": day3_exercises
    }

    # ==================== DAY 4: LEGS ====================
    Legs_df = df_csv[df_csv['Muscle_Group'] == 'Legs']

    day4_exercises = []
    variation_Legs = None

    if not Legs_df.empty:
        variation_Legs = random.choice(Legs_df['Workout_Variation'].unique())
        leg_exercises = Legs_df[Legs_df['Workout_Variation'] == variation_Legs].sort_values('Exercise_Number')
        for _, row in leg_exercises.iterrows():
            sr = get_sets_reps(level, row['Exercise_Type'])
            day4_exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })

    # Always add Deadlifts
    sr = get_sets_reps(level, "Compound")
    day4_exercises.append({
        "exercise_name": "Deadlifts",
        "muscle_group": "Legs",
        "exercise_type": "Compound",
        "sets": sr["sets"],
        "reps": sr["reps"]
    })

    day4 = {
        "variations": {"Legs": variation_Legs},
        "workout": day4_exercises
    }

    if INCLUDE_CORE:
        add_core_and_accessory(day1, dataset, week_index, set(), phase, level, goal, detail)
        add_core_and_accessory(day2, dataset, week_index, set(), phase, level, goal, detail)
        add_core_and_accessory(day3, dataset, week_index, set(), phase, level, goal, detail)
        add_core_and_accessory(day4, dataset, week_index, set(), phase, level, goal, detail)

    return {
        "day1": {"day_type": "Chest & Triceps", **day1},
        "day2": {"day_type": "Back & Biceps", **day2},
        "day3": {"day_type": "Shoulders", **day3},
        "day4": {"day_type": "Legs", **day4}
    }


def generate_plan_five_days(user_id, level, dataset, week_index, phase, goal, detail):
    df_csv = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()
    user_level = level

    chest_day = generate_workout_chest_day_df(df_csv, df_excel, user_fitness_level=user_level)
    back_day = generate_workout_back_day_df(df_csv, df_excel, user_fitness_level=user_level)
    legs_day = generate_workout_leg_day_df(df_csv, df_excel, user_fitness_level=user_level)
    shoulders_day = generate_workout_shoulder_day_df(df_csv, df_excel, user_fitness_level=user_level)

    arms_day = generate_workout_arms_day_df(df_excel, user_fitness_level=user_level)
    if not arms_day.get("workout"):
        arms_day = generate_workout_arms_from_csv(df_csv, user_fitness_level=user_level)

    if INCLUDE_CORE:
        for day in [chest_day, back_day, legs_day, shoulders_day, arms_day]:
            d = {"variations": day.get("variations", {}), "workout": day.get("workout", [])}
            add_core_and_accessory(d, dataset, week_index, set(), phase, level, goal, detail)
            day["workout"] = d["workout"]

    return {
        "day1": {"day_type": "Chest", **chest_day},
        "day2": {"day_type": "Back", **back_day},
        "day3": {"day_type": "Shoulders", **shoulders_day},
        "day4": {"day_type": "Legs", **legs_day},
        "day5": {"day_type": "Arms", **arms_day}
    }


def generate_workout_arms_from_csv(df_csv, user_fitness_level="beginner"):
    biceps_df = df_csv[df_csv['Muscle_Group'] == 'Biceps']
    triceps_df = df_csv[df_csv['Muscle_Group'] == 'Triceps']

    biceps_var = random.choice(biceps_df['Workout_Variation'].unique()) if not biceps_df.empty else None
    triceps_var = random.choice(triceps_df['Workout_Variation'].unique()) if not triceps_df.empty else None

    exercises = []
    used_names = set()

    if biceps_var:
        biceps_ex = biceps_df[biceps_df['Workout_Variation'] == biceps_var].sort_values('Exercise_Number')
        for _, row in biceps_ex.iterrows():
            sr = get_sets_reps(user_fitness_level, row['Exercise_Type'])
            exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names.add(row['Exercise_Name'])

    if triceps_var:
        triceps_ex = triceps_df[triceps_df['Workout_Variation'] == triceps_var].sort_values('Exercise_Number')
        for _, row in triceps_ex.iterrows():
            sr = get_sets_reps(user_fitness_level, row['Exercise_Type'])
            exercises.append({
                "exercise_name": row['Exercise_Name'],
                "muscle_group": row['Muscle_Group'],
                "exercise_type": row['Exercise_Type'],
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
            used_names.add(row['Exercise_Name'])

    return {
        "variations": {"Biceps": biceps_var, "Triceps": triceps_var},
        "workout": exercises
    }


def generate_workout_day_from_excel(user_id, fitness_level, muscle_group, excel_path=BRO_SPLIT_XLSX):
    exercises = []
    variations = {}

    if os.path.exists(excel_path):
        try:
            df_excel = pd.read_excel(excel_path)
        except Exception:
            df_excel = pd.DataFrame()
    else:
        df_excel = pd.DataFrame()

    if df_excel.empty or 'Muscle_Group' not in df_excel.columns:
        return {
            "user_id": user_id,
            "day_type": muscle_group,
            "fitness_level": fitness_level,
            "variations": {},
            "workout": []
        }

    mg_df = df_excel[df_excel['Muscle_Group'] == muscle_group]
    if mg_df.empty:
        return {
            "user_id": user_id,
            "day_type": muscle_group,
            "fitness_level": fitness_level,
            "variations": {},
            "workout": []
        }

    variation = random.choice(mg_df['Workout_Variation'].unique())
    variations[muscle_group] = variation

    workout_df = mg_df[mg_df['Workout_Variation'] == variation].sort_values('Exercise_Number')

    for _, row in workout_df.iterrows():
        sr = get_sets_reps(fitness_level, row.get('Exercise_Type', 'Isolation'))
        exercises.append({
            "exercise_name": row.get('Exercise_Name', ''),
            "muscle_group": row.get('Muscle_Group', muscle_group),
            "exercise_type": row.get('Exercise_Type', 'Isolation'),
            "sets": sr["sets"],
            "reps": sr["reps"]
        })

    return {
        "user_id": user_id,
        "day_type": muscle_group,
        "fitness_level": fitness_level,
        "variations": variations,
        "workout": exercises
    }