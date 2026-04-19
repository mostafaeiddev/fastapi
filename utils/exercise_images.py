import re

# ✅ حط كل الصور هنا
CLOUDINARY_MAP = {
    "barbell bench press": "https://res.cloudinary.com/duprntyar/image/upload/v1776339493/moveon/Final_Images/Close%2BGrip%2BBarbell%2BBench%2BPress.webp",
    "dumbbell bench press": "https://res.cloudinary.com/duprntyar/image/upload/v1776339498/moveon/Final_Images/dumbbell-bench-press.jpg.webp",
    "machine bench press": "https://res.cloudinary.com/duprntyar/image/upload/v1776339512/moveon/Final_Images/Machine%20Bench%20Press.webp",
    "rope pushdowns": "https://res.cloudinary.com/duprntyar/image/upload/v1776339518/moveon/Final_Images/Rope%20Pushdowns.webp",
    "lat pulldowns": "https://res.cloudinary.com/duprntyar/image/upload/v1776339507/moveon/Final_Images/Lat%20Pulldowns.webp",
    "dumbbell rows": "https://res.cloudinary.com/duprntyar/image/upload/v1776339497/moveon/Final_Images/Dumbbell%20Rows.webp",
    "seated rows close-grip": "https://res.cloudinary.com/duprntyar/image/upload/v1776339523/moveon/Final_Images/Seated%20Rows%20Close-Grip.webp",
    "cable curls": "https://res.cloudinary.com/duprntyar/image/upload/v1776339491/moveon/Final_Images/Cable%20Curls.webp",
    "incline dumbbell curls": "https://res.cloudinary.com/duprntyar/image/upload/v1776339505/moveon/Final_Images/Incline%20Dumbbell%20Curls.webp",
    "barbell rows": "https://res.cloudinary.com/duprntyar/image/upload/v1776339488/moveon/Final_Images/Barbell%20Rows.webp",
    "machine shoulder press": "https://res.cloudinary.com/duprntyar/image/upload/v1776339513/moveon/Final_Images/Machine%20Shoulder%20Press.webp",
    "face pulls": "https://res.cloudinary.com/duprntyar/image/upload/v1776339500/moveon/Final_Images/Face%20Pulls.webp",
    "cable lateral raises": "https://res.cloudinary.com/duprntyar/image/upload/v1776339491/moveon/Final_Images/Cable%20Lateral%20Raises.webp",
    "dumbbell lunges": "https://res.cloudinary.com/duprntyar/image/upload/v1776339511/moveon/Final_Images/Lunges.webp",
    "lying leg curl": "https://res.cloudinary.com/duprntyar/image/upload/v1776339512/moveon/Final_Images/Lying%20Leg%20Curl.webp",
    "leg extensions": "https://res.cloudinary.com/duprntyar/image/upload/v1776339508/moveon/Final_Images/Leg%20Extensions.webp",
    "seated calf raises": "https://res.cloudinary.com/duprntyar/image/upload/v1776339521/moveon/Final_Images/Seated%20Calf%20Raises.webp",
    "hip adductor machine": "https://res.cloudinary.com/duprntyar/image/upload/v1776339504/moveon/Final_Images/Hip%20Adductor%20Machine.webp",
    "romanian deadlift": "https://res.cloudinary.com/duprntyar/image/upload/v1776339517/moveon/Final_Images/Romani%20Deadleft.webp",
}

# fallback لو مش لاقي
DEFAULT_IMAGE = "https://res.cloudinary.com/duprntyar/image/upload/v1776339512/moveon/Final_Images/Machine%20Bench%20Press.webp"


def normalize(text: str):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def get_image_url(exercise_name: str):
    if not exercise_name:
        return DEFAULT_IMAGE

    name = exercise_name.lower().strip()

    # direct match
    if name in CLOUDINARY_MAP:
        return CLOUDINARY_MAP[name]

    normalized_name = normalize(name)

    # exact normalized match
    for key, url in CLOUDINARY_MAP.items():
        if normalize(key) == normalized_name:
            return url

    # partial match
    for key, url in CLOUDINARY_MAP.items():
        if normalized_name in normalize(key) or normalize(key) in normalized_name:
            return url

    return DEFAULT_IMAGE