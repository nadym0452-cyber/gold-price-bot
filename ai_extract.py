import os
import json
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

GOVERNORATES = [
    "القاهرة", "الجيزة", "الإسكندرية", "الفيوم", "المنوفية", "الشرقية",
    "الدقهلية", "البحيرة", "الغربية", "كفر الشيخ", "دمياط", "بورسعيد",
    "الإسماعيلية", "السويس", "شمال سيناء", "جنوب سيناء", "بني سويف",
    "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "البحر الأحمر",
    "الوادي الجديد", "مطروح", "القليوبية",
]


def extract_shop_data(raw_text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

    gov_list = "، ".join(GOVERNORATES)

    prompt = (
        f"النص التالي يصف محل ذهب أو مجوهرات بشكل غير منظم:\n\n"
        f"\"{raw_text}\"\n\n"
        f"استخرج منه البيانات وأرجعها كـ JSON فقط بدون أي نص إضافي أو علامات markdown، "
        f"بالضبط بالشكل ده:\n"
        f'{{"shop_name": "", "governorate": "", "city": "", "address": "", "phone": "", "whatsapp": ""}}\n\n'
        f"قواعد مهمة:\n"
        f"- قيمة governorate لازم تكون واحدة بالضبط من هذه القائمة: {gov_list} — أو نص فارغ لو مش واضحة\n"
        f"- وحّد رقم الهاتف ليبدأ بصفر ويكون 11 رقم لو ممكن\n"
        f"- لو أي حقل مش موجود في النص، خليه نص فارغ\n"
        f"- لو النص مش متعلق بمحل ذهب خالص، أرجع shop_name فارغ"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    return json.loads(text)
