import cloudinary
import cloudinary.uploader
import os

# -------------------------
# حط بياناتك هنا
# -------------------------
CLOUD_NAME = "duprntyar"
API_KEY = "912576765793331"
API_SECRET = "aFe3oFgQKqICHMH_BAMXAqfPruM"
IMAGES_DIR = "Images"  # فولدر الصور (نفس مكان السكريبت)
# -------------------------

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def upload_all():
    if not os.path.exists(IMAGES_DIR):
        print(f"❌ مش لاقي فولدر: {IMAGES_DIR}")
        return

    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.webp', '.jpg', '.jpeg', '.png'))]
    print(f"📦 هيرفع {len(files)} صورة...\n")

    success, failed = [], []

    for filename in files:
        filepath = os.path.join(IMAGES_DIR, filename)
        # اسم الصورة بدون extension كـ public_id
        public_id = os.path.splitext(filename)[0]

        try:
            result = cloudinary.uploader.upload(
                filepath,
                public_id=public_id,
                folder="moveon/exercises",   # فولدر في Cloudinary
                overwrite=True,
                resource_type="image"
            )
            url = result.get("secure_url")
            print(f"✅ {filename} → {url}")
            success.append({"filename": filename, "url": url, "public_id": public_id})
        except Exception as e:
            print(f"❌ {filename} → {e}")
            failed.append(filename)

    print(f"\n✅ نجح: {len(success)} | ❌ فشل: {len(failed)}")

    # احفظ الـ URLs في ملف عشان تستخدمها بعدين
    if success:
        import json
        with open("cloudinary_urls.json", "w", encoding="utf-8") as f:
            json.dump(success, f, ensure_ascii=False, indent=2)
        print("💾 الـ URLs اتحفظت في cloudinary_urls.json")

if __name__ == "__main__":
    upload_all()