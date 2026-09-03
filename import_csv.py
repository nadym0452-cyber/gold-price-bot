import csv
import sys
from database import init_db, add_shop

def import_from_csv(filepath):
    init_db()
    count = 0
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            add_shop(
                shop_name=row.get("shop_name", "").strip(),
                governorate=row.get("governorate", "").strip(),
                city=row.get("city", "").strip(),
                address=row.get("address", "").strip(),
                phone=row.get("phone", "").strip(),
                whatsapp=row.get("whatsapp", "").strip(),
                maps_url=row.get("maps_url", "").strip(),
                source_url=row.get("source", "").strip(),
                status="Needs Review",
            )
            count += 1
    print(f"تم استيراد {count} محل بنجاح. الحالة الافتراضية: Needs Review (يحتاج مراجعة)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام: python import_csv.py اسم_الملف.csv")
    else:
        import_from_csv(sys.argv[1])
