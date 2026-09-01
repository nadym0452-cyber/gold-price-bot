import os
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


def fetch_gold_price_usd():
    resp = requests.get("https://api.gold-api.com/price/XAU", timeout=30)
    resp.raise_for_status()
    return resp.json()["price"]


def fetch_usd_to_egp():
    resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=30)
    resp.raise_for_status()
    return resp.json()["rates"]["EGP"]


def calculate_prices(gold_usd, egp_rate):
    ounce_egp = gold_usd * egp_rate
    gram24 = ounce_egp / 31.1035
    gram21 = gram24 * (21 / 24)
    gram18 = gram24 * (18 / 24)
    return round(gram24, 2), round(gram21, 2), round(gram18, 2)


def get_ai_analysis(gram24, gram21, gram18, usd_rate):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = (
        f"أنت محلل أسواق مالية محترف متخصص في سوق الذهب. "
        f"سعر جرام الذهب عيار 24 دلوقتي هو {gram24} جنيه، عيار 21 هو {gram21} جنيه، وعيار 18 هو {gram18} جنيه. "
        f"سعر الدولار مقابل الجنيه هو {usd_rate}. "
        f"اكتب 3 جمل قصيرة منفصلة بالعامية المصرية البسيطة، كل جملة توصف نقطة مختلفة، "
        f"وافصل بين كل جملة والتانية بالرمز |||  بدون أي ترقيم أو عناوين قبلها:\n"
        f"1) جملة عن حالة السوق المحلي وضغط الشراء أو البيع الحالي\n"
        f"2) جملة عن تأثير حركة سعر الدولار على تسعير الذهب\n"
        f"3) جملة عن الوضع الفني العام وحالة التوازن بين العرض والطلب\n"
        f"ممنوع منعا باتا استخدام اي عبارة تحث على الشراء او البيع او تصف الوضع بأنه فرصة. "
        f"اكتفِ بوصف الحالة كمراقب محايد تماما."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parts = [p.strip() for p in text.split("|||")]
        while len(parts) < 3:
            parts.append("لا تتوفر بيانات كافية حاليا.")
        return parts[0], parts[1], parts[2]
    except Exception as e:
        err = f"تعذر توليد التحليل حاليا ({e})"
        return err, err, err


def send_analysis_message(gram24, gram21, gram18, usd_rate):
    local_market, dollar_effect, technical = get_ai_analysis(gram24, gram21, gram18, usd_rate)

    message = (
        f"💰 أسعار الذهب اليوم\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"⚡عيار (24) ⬅️ {gram24} جنيه\n\n"
        f"⚡عيار (21) ⬅️ {gram21} جنيه\n\n"
        f"⚡عيار (18) ⬅️ {gram18} جنيه\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 تحليل السوق ⬇️\n\n"
        f"🌐 السوق المحلي ⬅️ {local_market}\n\n"
        f"💵 حركة سعر الدولار ⬅️ {dollar_effect}\n\n"
        f"📝 الوضع الفني ⬅️ {technical}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚠️ هذا وصف لحالة السوق فقط وليس توصية بالشراء أو البيع"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=30)


def main():
    gold_usd = fetch_gold_price_usd()
    egp_rate = fetch_usd_to_egp()
    gram24, gram21, gram18 = calculate_prices(gold_usd, egp_rate)
    send_analysis_message(gram24, gram21, gram18, egp_rate)


if __name__ == "__main__":
    main()
