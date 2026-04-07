#!/usr/bin/env python3
# Ex.py
# Usage (called from C#): py Ex.py "<userId>" "<userName>" "<activitylevel>" "<goal>" <availableDays>
# Example: py Ex.py "123" "Moustafa" "1" "muscle_gain" 3

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
# Set to True to include Core/Abs exercises
INCLUDE_CORE = False

# -------------------------
# Helpers
# -------------------------
def safe_print_json(obj):
    try:
        print(json.dumps(obj, ensure_ascii=False))
    except Exception:
        # fallback minimal error JSON
        print(json.dumps({"status":"error","message":"Failed to serialize output"}))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def parse_activity_level(val):
    # Accept numeric or string
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
DATA_CSV = os.path.join(os.path.dirname(__file__), "all_workouts_final.csv")
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
    # fuzzy simple checks
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
                    # normalize keys
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
            # fall through to sample
            pass

    # Fallback sample dataset (minimal, ensures script always works)
    sample = [
        {"Exercise_Name":"Bench Press","Muscle_Group":"Chest","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Incline Dumbbell Press","Muscle_Group":"Chest","Exercise_Type":"Compound","Workout_Variation":"Dumbbell","Exercise_Number":2,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Chest Fly","Muscle_Group":"Chest","Exercise_Type":"Isolation","Workout_Variation":"Machine","Exercise_Number":3,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Overhead Press","Muscle_Group":"Shoulders","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Lateral Raise","Muscle_Group":"Shoulders","Exercise_Type":"Isolation","Workout_Variation":"Dumbbell","Exercise_Number":2,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Triceps Pushdown","Muscle_Group":"Triceps","Exercise_Type":"Isolation","Workout_Variation":"Cable","Exercise_Number":1,"Primary_Equipment":"Cable"},
        {"Exercise_Name":"Pull Ups","Muscle_Group":"Back","Exercise_Type":"Compound","Workout_Variation":"Bodyweight","Exercise_Number":1,"Primary_Equipment":"Bodyweight"},
        {"Exercise_Name":"Barbell Row","Muscle_Group":"Back","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":2,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Bicep Curl","Muscle_Group":"Biceps","Exercise_Type":"Isolation","Workout_Variation":"Dumbbell","Exercise_Number":1,"Primary_Equipment":"Dumbbell"},
        {"Exercise_Name":"Squat","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":1,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Leg Press","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Machine","Exercise_Number":2,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Leg Curl","Muscle_Group":"Legs","Exercise_Type":"Isolation","Workout_Variation":"Machine","Exercise_Number":3,"Primary_Equipment":"Machine"},
        {"Exercise_Name":"Deadlift","Muscle_Group":"Legs","Exercise_Type":"Compound","Workout_Variation":"Barbell","Exercise_Number":4,"Primary_Equipment":"Barbell"},
        {"Exercise_Name":"Plank","Muscle_Group":"Core","Exercise_Type":"Isolation","Workout_Variation":"Bodyweight","Exercise_Number":1,"Primary_Equipment":"Bodyweight"},
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

    # minimal progressive overload for week 1 (no big change)
    if phase == "Hypertrophy":
        min_rep += (week_index - 1)
        max_rep += (week_index - 1)
    elif phase == "Strength":
        min_rep = max(3, min_rep - 2)
        max_rep = max(5, max_rep - 2)
    elif phase == "Endurance":
        min_rep += 3
        max_rep += 3

    # goal adjustments
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
    """
    Helper: return list of rows (as dicts) for chosen_variation,
    and if count < min_needed, append rows from other variations (no duplicates)
    until min_needed or exhausted.
    """
    if df_group.empty:
        return []

    # all rows for chosen variation
    primary = df_group[df_group['Workout_Variation'] == chosen_variation].sort_values('Exercise_Number')
    collected = list(primary.to_dict(orient='records'))

    if len(collected) >= min_needed:
        return collected

    # need to fill from other variations (ordered by Exercise_Number)
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
    # try multiple filenames (Bro_Split.xlsx, pro_split.xlsx, Pro_Split.xlsx)
    for p in (BRO_SPLIT_XLSX, PRO_SPLIT_XLSX, PRO_SPLIT_XLSX_ALT):
        if os.path.exists(p):
            try:
                return pd.read_excel(p)
            except Exception:
                continue
    return pd.DataFrame()
def generate_workout_chest_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    """
    Generate chest workout using Excel if available, otherwise use CSV
    Returns ALL exercises for the chosen variation
    """
    # Try Excel first (Bro_Split.xlsx usually has good chest exercises)
    chest_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        chest_df = df_excel[df_excel['Muscle_Group'] == 'Chest']
    
    # Fallback to CSV if Excel has no chest data
    if chest_df.empty:
        chest_df = df_csv[df_csv['Muscle_Group'] == 'Chest']
    
    # Choose random variation
    variation_Chest = random.choice(list(chest_df['Workout_Variation'].unique())) if not chest_df.empty else None
    
    # Return ALL exercises for the chosen variation
    workout_df = pd.DataFrame()
    if variation_Chest:
        workout_df = chest_df[chest_df['Workout_Variation'] == variation_Chest].sort_values('Exercise_Number')
    
    rows = workout_df.to_dict(orient='records')
    
    exercises = []
    for row in rows:
        ex_type = row.get('Exercise_Type') or row.get('exercise_type', 'Compound')
        ex_name = row.get('Exercise_Name') or row.get('exercise_name', '')
        muscle = row.get('Muscle_Group') or row.get('muscle_group', 'Chest')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": muscle,
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
    
    return {"variations": {"Chest": variation_Chest}, "workout": exercises}


def generate_workout_back_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    """
    Generate back workout using Excel if available, otherwise use CSV
    Returns ALL exercises for the chosen variation
    """
    # Try Excel first
    back_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        back_df = df_excel[df_excel['Muscle_Group'] == 'Back']
    
    # Fallback to CSV if Excel has no back data
    if back_df.empty:
        back_df = df_csv[df_csv['Muscle_Group'] == 'Back']
    
    # Choose random variation
    variation_Back = random.choice(list(back_df['Workout_Variation'].unique())) if not back_df.empty else None
    
    # Return ALL exercises for the chosen variation
    workout_df = pd.DataFrame()
    if variation_Back:
        workout_df = back_df[back_df['Workout_Variation'] == variation_Back].sort_values('Exercise_Number')
    
    rows = workout_df.to_dict(orient='records')
    
    exercises = []
    for row in rows:
        ex_type = row.get('Exercise_Type') or row.get('exercise_type', 'Compound')
        ex_name = row.get('Exercise_Name') or row.get('exercise_name', '')
        muscle = row.get('Muscle_Group') or row.get('muscle_group', 'Back')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": muscle,
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
    
    return {"variations": {"Back": variation_Back}, "workout": exercises}


def generate_workout_leg_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    """
    Generate leg workout using Excel if available, otherwise use CSV
    Returns ALL exercises for the chosen variation, plus Deadlifts
    """
    # Try Excel first
    legs_df = pd.DataFrame()
    if df_excel is not None and not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        legs_df = df_excel[df_excel['Muscle_Group'] == 'Legs']
    
    # Fallback to CSV if Excel has no leg data
    if legs_df.empty:
        if df_csv is not None and not df_csv.empty:
            legs_df = df_csv[df_csv['Muscle_Group'] == 'Legs']
    
    # Choose random variation if data exists
    variation_Legs = None
    if not legs_df.empty and 'Workout_Variation' in legs_df.columns:
        unique_variations = legs_df['Workout_Variation'].unique()
        if len(unique_variations) > 0:
            variation_Legs = random.choice(list(unique_variations))
    
    # Get exercises for chosen variation
    exercises = []
    
    if variation_Legs and not legs_df.empty:
        # Get exercises for the chosen variation
        workout_df = legs_df[legs_df['Workout_Variation'] == variation_Legs].sort_values('Exercise_Number')
        
        for _, row in workout_df.iterrows():
            # Get exercise type safely
            ex_type = row.get('Exercise_Type', 'Compound')
            if pd.isna(ex_type):
                ex_type = 'Compound'
            
            # Get sets and reps
            sr = get_sets_reps(user_fitness_level, ex_type)
            
            exercises.append({
                "exercise_name": row.get('Exercise_Name', 'Unknown'),
                "muscle_group": row.get('Muscle_Group', 'Legs'),
                "exercise_type": ex_type,
                "sets": sr["sets"],
                "reps": sr["reps"]
            })
    
    # Always include Deadlifts as compound
    sr = get_sets_reps(user_fitness_level, "Compound")
    exercises.append({
        "exercise_name": "Deadlifts",
        "muscle_group": "Legs",
        "exercise_type": "Compound",
        "sets": sr["sets"],
        "reps": sr["reps"]
    })
    
    return {
        "variations": {"Legs": variation_Legs},
        "workout": exercises
    }

def generate_workout_shoulder_day_df(df_csv, df_excel, user_fitness_level="beginner"):
    """
    Generate shoulder workout using Excel if available, otherwise use CSV
    Returns ALL exercises for the chosen variation
    """
    # Try Excel first (Shoulders often have good data in Bro_Split.xlsx)
    shoulder_df = pd.DataFrame()
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        shoulder_df = df_excel[df_excel['Muscle_Group'] == 'Shoulders']
    
    # Fallback to CSV if Excel has no shoulder data
    if shoulder_df.empty:
        shoulder_df = df_csv[df_csv['Muscle_Group'] == 'Shoulders']
    
    # Choose random variation
    variation = random.choice(list(shoulder_df['Workout_Variation'].unique())) if not shoulder_df.empty else None
    
    # Get exercises for chosen variation
    workout_df = pd.DataFrame()
    if variation:
        # Handle column name variations
        if 'Workout_Variation' in shoulder_df.columns:
            workout_df = shoulder_df[shoulder_df['Workout_Variation'] == variation].sort_values('Exercise_Number')
        else:
            workout_df = shoulder_df[shoulder_df['Workout_Variation'] == variation].sort_values('Exercise_Number')
    
    exercises = []
    for _, row in workout_df.iterrows():
        ex_type = row.get('Exercise_Type', 'Isolation')
        ex_name = row.get('Exercise_Name', '')
        muscle = row.get('Muscle_Group', 'Shoulders')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": muscle,
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
    
    return {"variations": {"Shoulders": variation}, "workout": exercises}

def generate_workout_arms_day_df(df_excel, user_fitness_level="beginner"):
    """
    Generate arms workout using Excel only (Bro_Split.xlsx)
    Uses Arms as a single muscle group with one variation
    """
    if df_excel.empty or 'Muscle_Group' not in df_excel.columns:
        return {"variations": {}, "workout": []}
    
    # Get Arms exercises (Arms as a single muscle group)
    arms_df = df_excel[df_excel['Muscle_Group'].str.lower() == 'arms']
    
    if arms_df.empty:
        return {"variations": {}, "workout": []}
    
    # Choose a single variation for Arms
    arms_variation = random.choice(arms_df['Workout_Variation'].unique())
    
    # Get all exercises for the chosen variation
    arms_workout_df = arms_df[arms_df['Workout_Variation'] == arms_variation].sort_values('Exercise_Number')
    
    # Minimum total exercises for arms day
    MIN_ARMS_TOTAL = 5
    
    # If we don't have enough exercises, add more from other variations
    if len(arms_workout_df) < MIN_ARMS_TOTAL:
        other_exercises = arms_df[arms_df['Workout_Variation'] != arms_variation].sort_values('Exercise_Number')
        
        # Get existing exercise names to avoid duplicates
        existing_names = set(arms_workout_df['Exercise_Name'].tolist())
        
        # Add exercises from other variations until we reach MIN_ARMS_TOTAL
        additional_rows = []
        for _, row in other_exercises.iterrows():
            if row['Exercise_Name'] not in existing_names:
                additional_rows.append(row)
                existing_names.add(row['Exercise_Name'])
                if len(arms_workout_df) + len(additional_rows) >= MIN_ARMS_TOTAL:
                    break
        
        # Combine original and additional exercises
        if additional_rows:
            arms_workout_df = pd.concat([arms_workout_df, pd.DataFrame(additional_rows)], ignore_index=True)
    
    # Convert to workout format with sets/reps
    exercises = []
    for _, row in arms_workout_df.iterrows():
        ex_type = row.get('Exercise_Type', 'Isolation')
        ex_name = row.get('Exercise_Name', '')
        muscle = row.get('Muscle_Group', 'Arms')
        sr = get_sets_reps(user_fitness_level, ex_type)
        exercises.append({
            "exercise_name": ex_name,
            "muscle_group": muscle,  # This will be "Arms"
            "exercise_type": ex_type,
            "sets": sr["sets"],
            "reps": sr["reps"]
        })
    
    return {
        "variations": {"Arms": arms_variation},  # Single variation for Arms
        "workout": exercises
    }

def generate_workout_push_day(df, user_fitness_level="beginner"):
    Chest_df = df[df['Muscle_Group'] == 'Chest']
    Shoulder_df = df[df['Muscle_Group'] == 'Shoulders']
    Triceps_df = df[df['Muscle_Group'] == 'Triceps']

    variation_Chest = random.choice(list(Chest_df['Workout_Variation'].unique())) if not Chest_df.empty else None
    variation_Shoulder = random.choice(list(Shoulder_df['Workout_Variation'].unique())) if not Shoulder_df.empty else None if 'Workout_Variation' in Shoulder_df.columns else random.choice(list(Shoulder_df['Workout_Variation'].unique())) if not Shoulder_df.empty else None
    variation_Triceps = random.choice(list(Triceps_df['Workout_Variation'].unique())) if not Triceps_df.empty else None

    parts = []
    if variation_Chest:
        parts.append(Chest_df[Chest_df['Workout_Variation'] == variation_Chest].sort_values('Exercise_Number'))
    if variation_Shoulder:
        # handle possible column name casing issues
        if 'Workout_Variation' in Shoulder_df.columns:
            parts.append(Shoulder_df[Shoulder_df['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number'))
        else:
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

def generate_plan_one_day(user_id, level, dataset, week_index, phase, goal, detail):
    day = build_day(["Chest","Back","Legs","Shoulders","Biceps","Triceps"],
                    dataset, week_index, set(), set(), phase, level, goal, detail, full_day=True)
    add_core_and_accessory(day, dataset, week_index, set(), phase, level, goal, detail)
    return {"day1": {"day_type":"Full Body", **day}}

def generate_plan_two_days(user_id,  level, dataset, week_index, phase, goal, detail):
    upper_groups = ["Chest","Back","Shoulders","Biceps","Triceps"]
    d1 = build_day(upper_groups, dataset, week_index, set(), set(), phase, level, goal, detail, full_day=False)
    add_core_and_accessory(d1, dataset, week_index, set(), phase, level, goal, detail)
    d2 = build_day(["Legs"], dataset, week_index, set(), set(), phase, level, goal, detail, full_day=False)
    add_core_and_accessory(d2, dataset, week_index, set(), phase, level, goal, detail)
    return {"day1": {"day_type":"Upper Body", **d1}, "day2": {"day_type":"Lower Body", **d2}}

def generate_plan_three_days(user_id, level, dataset, week_index, phase, goal, detail):
    df = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()  # Load Excel (ممكن يكون فاضي)
    user_level = level
    
    # Push and Pull don't need Excel
    push = generate_workout_push_day(df, user_fitness_level=user_level)
    pull = generate_workout_pull_day(df, user_fitness_level=user_level)
    
    # Legs needs Excel parameter (pass None if you don't have it)
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
    """
    Simple 4-day plan generator using the exact logic from your snippets
    """
    df_csv = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()
    
    # ==================== DAY 1: CHEST + TRICEPS ====================
    Chest_df = df_csv[df_csv['Muscle_Group'] == 'Chest']
    Triceps_df = df_csv[df_csv['Muscle_Group'] == 'Triceps']
    
    variation_Chest = random.choice(Chest_df['Workout_Variation'].unique()) if not Chest_df.empty else None
    variation_Triceps = random.choice(Triceps_df['Workout_Variation'].unique()) if not Triceps_df.empty else None
    
    day1_exercises = []
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
    
    day2 = {
        "variations": {"Back": variation_Back, "Biceps": variation_Biceps},
        "workout": day2_exercises
    }
    
    # ==================== DAY 3: SHOULDERS (from Excel) ====================
    day3_exercises = []
    variation_Shoulder = None
    
    # Try Excel first
    if not df_excel.empty and 'Muscle_Group' in df_excel.columns:
        shoulder_df = df_excel[df_excel['Muscle_Group'] == 'Shoulders']
        if not shoulder_df.empty:
            variation_Shoulder = random.choice(shoulder_df['Workout_Variation'].unique())
            shoulder_exercises = shoulder_df[shoulder_df['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number')
            for _, row in shoulder_exercises.iterrows():
                sr = get_sets_reps(level, row.get('Exercise_Type', 'Isolation'))
                day3_exercises.append({
                    "exercise_name": row.get('Exercise_Name', ''),
                    "muscle_group": row.get('Muscle_Group', 'Shoulders'),
                    "exercise_type": row.get('Exercise_Type', 'Isolation'),
                    "sets": sr["sets"],
                    "reps": sr["reps"]
                })
    
    # Fallback to CSV if Excel didn't work
    if not day3_exercises:
        shoulder_df_csv = df_csv[df_csv['Muscle_Group'] == 'Shoulders']
        if not shoulder_df_csv.empty:
            variation_Shoulder = random.choice(shoulder_df_csv['Workout_Variation'].unique())
            shoulder_exercises = shoulder_df_csv[shoulder_df_csv['Workout_Variation'] == variation_Shoulder].sort_values('Exercise_Number')
            for _, row in shoulder_exercises.iterrows():
                sr = get_sets_reps(level, row['Exercise_Type'])
                day3_exercises.append({
                    "exercise_name": row['Exercise_Name'],
                    "muscle_group": row['Muscle_Group'],
                    "exercise_type": row['Exercise_Type'],
                    "sets": sr["sets"],
                    "reps": sr["reps"]
                })
    
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
    
    # Add Deadlifts
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
    
    # Add core if enabled
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
    """
    5-day plan:
    - day1: Chest (Chest only)
    - day2: Back (Back only)
    - day3: Shoulders (Shoulders only, prefer Bro_Split.xlsx)
    - day4: Legs (Legs only)
    - day5: Arms (Arms as single muscle group from Excel)
    """
    df_csv = pd.DataFrame(dataset)
    df_excel = _load_shoulder_excel()  # Load Excel once
    
    user_level = level

    # Pass both CSV and Excel to all functions
    chest_day = generate_workout_chest_day_df(df_csv, df_excel, user_fitness_level=user_level)
    back_day = generate_workout_back_day_df(df_csv, df_excel, user_fitness_level=user_level)
    legs_day = generate_workout_leg_day_df(df_csv, df_excel, user_fitness_level=user_level)
    shoulders_day = generate_workout_shoulder_day_df(df_csv, df_excel, user_fitness_level=user_level)

    # Arms: use Excel with Arms as single muscle group
    arms_day = generate_workout_arms_day_df(df_excel, user_fitness_level=user_level)
    
    # Fallback if arms_day is empty (Excel doesn't have Arms)
    if not arms_day.get("workout"):
        # Try to get from CSV by combining Biceps and Triceps
        arms_day = generate_workout_arms_from_csv(df_csv, user_fitness_level=user_level)

    # Add core/accessory if enabled
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


def _load_shoulder_excel():
    """Load Excel file (Bro_Split.xlsx) if it exists"""
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
    
    return pd.DataFrame()  # Return empty DataFrame if no Excel file found



def generate_workout_arms_from_csv(df_csv, user_fitness_level="beginner"):
    """
    Fallback function to generate arms workout from CSV
    Combines Biceps and Triceps into one day
    """
    biceps_df = df_csv[df_csv['Muscle_Group'] == 'Biceps']
    triceps_df = df_csv[df_csv['Muscle_Group'] == 'Triceps']
    
    # Choose variations
    biceps_var = random.choice(biceps_df['Workout_Variation'].unique()) if not biceps_df.empty else None
    triceps_var = random.choice(triceps_df['Workout_Variation'].unique()) if not triceps_df.empty else None
    
    exercises = []
    
    # Add Biceps exercises
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
    
    # Add Triceps exercises
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
    
    return {
        "variations": {"Biceps": biceps_var, "Triceps": triceps_var},
        "workout": exercises
    }

def generate_workout_day_from_excel(user_id, fitness_level, muscle_group, excel_path=BRO_SPLIT_XLSX):
    exercises = []
    variations = {}

    # load excel if exists
    if os.path.exists(excel_path):
        try:
            df_excel = pd.read_excel(excel_path)
        except Exception:
            df_excel = pd.DataFrame()
    else:
        df_excel = pd.DataFrame()

    if df_excel.empty or 'Muscle_Group' not in df_excel.columns:
        # return empty structure if excel not usable
        return {
            "user_id": user_id,
            #"user_name": user_name,
            "day_type": muscle_group,
            "fitness_level": fitness_level,
            "variations": {},
            "workout": []
        }

    mg_df = df_excel[df_excel['Muscle_Group'] == muscle_group]
    if mg_df.empty:
        return {
            "user_id": user_id,
            #"user_name": user_name,
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
       # "user_name": user_name,
        "day_type": muscle_group,
        "fitness_level": fitness_level,
        "variations": variations,
        "workout": exercises
    }

