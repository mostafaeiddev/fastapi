import cloudinary
import cloudinary.uploader
import os

CLOUD_NAME = "duprntyar"
API_KEY = "912576765793331"
API_SECRET = "aFe3oFgQKqICHMH_BAMXAqfPruM"
IMAGES_DIR = "Images"

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

    success = []

    for filename in files:
        filepath = os.path.join(IMAGES_DIR, filename)
        public_id = os.path.splitext(filename)[0]

        try:
            result = cloudinary.uploader.upload(
                filepath,
                public_id=public_id,
                folder="moveon/Final_Images",
                overwrite=True,
                resource_type="image",
                format="webp"   # 👈 مهم
            )

            url = result.get("secure_url")
            print(f"✅ {filename} → {url}")

            success.append({
                "filename": filename,
                "public_id": public_id,
                "url": url
            })

        except Exception as e:
            print(f"❌ {filename} → {e}")

    # حفظ اللينكات
    import json
    with open("cloudinary_urls.json", "w", encoding="utf-8") as f:
        json.dump(success, f, ensure_ascii=False, indent=2)

    print("💾 تم حفظ cloudinary_urls.json")

if __name__ == "__main__":
    upload_all()