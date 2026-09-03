from database import init_db, add_shop

init_db()

sample_shops = [
    {
        "shop_name": "مجوهرات الفيوم الذهبية",
        "governorate": "الفيوم",
        "city": "الفيوم",
        "address": "شارع الجمهورية، بجوار البنك الأهلي",
        "phone": "01000000001",
        "whatsapp": "01000000001",
        "maps_url": "https://maps.google.com/?q=فيوم+مركز",
        "source": "بيانات تجريبية للاختبار",
        "verified": "verified",
    },
    {
        "shop_name": "محلات الأمانة للمجوهرات",
        "governorate": "الفيوم",
        "city": "سنورس",
        "address": "شارع المحطة، سنورس",
        "phone": "01000000002",
        "whatsapp": None,
        "maps_url": None,
        "source": "بيانات تجريبية للاختبار",
        "verified": "verified",
    },
]

for shop in sample_shops:
    add_shop(**shop)

print(f"تمت إضافة {len(sample_shops)} محل تجريبي بنجاح.")
