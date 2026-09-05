import os
import re
import io
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# ---------- Settings ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SOURCE_URL = "https://www.gold-price-today.com/egypt/"

FONT_URL_REGULAR = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/noto-monthly-release-2025.12.01/fonts/NotoKufiArabic/hinted/ttf/NotoKufiArabic-Regular.ttf"
FONT_URL_BOLD = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/noto-monthly-release-2025.12.01/fonts/NotoKufiArabic/hinted/ttf/NotoKufiArabic-Bold.ttf"

FONT_REGULAR_PATH = "NotoKufiArabic-Regular.ttf"
FONT_BOLD_PATH = "NotoKufiArabic-Bold.ttf"

W, H = 1080, 300
BG = (8, 7, 6)
GOLD = (198, 155, 74)
GOLD_LIGHT = (232, 196, 128)
WHITE = (240, 240, 240)


def download_font():
    for url, path in [(FONT_URL_REGULAR, FONT_REGULAR_PATH), (FONT_URL_BOLD, FONT_BOLD_PATH)]:
        if not os.path.exists(path):
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)


def draw_rtl(d, xy, text, font, fill, anchor="mm"):
    try:
        d.text(xy, text, font=font, fill=fill, anchor=anchor,
               direction="rtl", language="ar")
    except (ImportError, TypeError, ValueError):
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        d.text(xy, bidi_text, font=font, fill=fill, anchor=anchor)


def clean_number(raw):
    digits = re.sub(r"[^\d]", "", raw)
    return f"{int(digits):,}".replace(",", "،")


ARABIC_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def fetch_prices():
    resp = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator=" ")

    def grab(label):
        m = re.search(label + r"[^\d]{0,20}?([\d,]{3,7})\s*جنيه", text)
        if not m:
            raise ValueError(f"Couldn't find price for {label}")
        return clean_number(m.group(1))

    return {
        "24": grab(r"عيار\s*24"),
        "21": grab(r"عيار\s*21"),
        "18": grab(r"عيار\s*18"),
        "pound": grab(r"الجنيه\s*الذهب"),
    }


def build_image(prices):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_price = ImageFont.truetype(FONT_BOLD_PATH, 80)
    f_label = ImageFont.truetype(FONT_BOLD_PATH, 36)
    f_datetime = ImageFont.truetype(FONT_BOLD_PATH, 32)
    f_badge = ImageFont.truetype(FONT_BOLD_PATH, 54)

    def text_rtl(xy, text, font, fill, anchor="mm"):
        draw_rtl(d, xy, text, font, fill, anchor)

    outer_margin = 20
    safe_margin = 110  # مساحة أمان إضافية عن الحواف عشان تليجرام ميقصش النص

    d.rounded_rectangle(
        (outer_margin, outer_margin, W - outer_margin, H - outer_margin),
        radius=24, outline=GOLD, width=3
    )

    now = datetime.now(ZoneInfo("Africa/Cairo"))
    date_str = f"{now.day} {ARABIC_MONTHS[now.month]}"
    hour12 = now.strftime("%I:%M").replace(":", "،")
    ampm = "م" if now.strftime("%p") == "PM" else "ص"
    time_str = f"{hour12} {ampm}"

    left_x = safe_margin
    right_x = W - safe_margin

    div_x2 = left_x + 190
    div_x = right_x - 190

    text_rtl((left_x + 100, H // 2 - 40), date_str, f_datetime, WHITE, anchor="rm")
    text_rtl((left_x + 100, H // 2 + 40), time_str, f_datetime, WHITE, anchor="rm")

    d.line([(div_x2, outer_margin + 25), (div_x2, H - outer_margin - 25)], fill=GOLD, width=2)

    price_cx = (div_x2 + div_x) // 2
    text_rtl((price_cx, H // 2), f"{prices['21']} جنيه", f_price, GOLD_LIGHT)

    d.line([(div_x, outer_margin + 25), (div_x, H - outer_margin - 25)], fill=GOLD, width=2)

    badge_cx = right_x - 30
    d.rounded_rectangle(
        (badge_cx - 60, H // 2 - 60, badge_cx + 60, H // 2 + 60), radius=18, fill=GOLD
    )
    d.text((badge_cx, H // 2), "21", font=f_badge, fill=(20, 15, 5), anchor="mm")
    text_rtl((badge_cx, H // 2 + 90), "عيار", f_label, GOLD)

    return img

    def text_rtl(xy, text, font, fill, anchor="mm"):
        draw_rtl(d, xy, text, font, fill, anchor)

    margin = 24
    d.rounded_rectangle((margin, margin, W - margin, H - margin), radius=24, outline=GOLD, width=3)

    now = datetime.now(ZoneInfo("Africa/Cairo"))
    date_str = f"{now.day} {ARABIC_MONTHS[now.month]}"
    hour12 = now.strftime("%I:%M").replace(":", "،")
    ampm = "م" if now.strftime("%p") == "PM" else "ص"
    time_str = f"{hour12} {ampm}"

    # Right section: label "عيار 21"
    right_cx = W - margin - 110
    d.rounded_rectangle(
        (right_cx - 70, H // 2 - 70, right_cx + 70, H // 2 + 70), radius=18, fill=GOLD
    )
    d.text((right_cx, H // 2), "21", font=ImageFont.truetype(FONT_BOLD_PATH, 60), fill=(20, 15, 5), anchor="mm")
    text_rtl((right_cx, H // 2 + 100), "عيار", f_label, GOLD)

    # Divider
    div_x = right_cx - 130
    d.line([(div_x, margin + 20), (div_x, H - margin - 20)], fill=GOLD, width=2)

    # Center: price (main focus)
    price_cx = (margin + div_x) // 2 + 90
    text_rtl((price_cx, H // 2), f"{prices['21']} جنيه", f_price, GOLD_LIGHT)

    # Left section: date & time stacked
    left_x = margin + 30
    div_x2 = margin + 220
    d.line([(div_x2, margin + 20), (div_x2, H - margin - 20)], fill=GOLD, width=2)
    text_rtl((left_x + 90, H // 2 - 40), date_str, f_datetime, WHITE, anchor="rm")
    text_rtl((left_x + 90, H // 2 + 40), time_str, f_datetime, WHITE, anchor="rm")

    return img


def send_to_telegram(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    resp = requests.post(
        url,
        data={"chat_id": CHAT_ID},
        files={"photo": ("gold_price.png", buf, "image/png")},
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")
    print("Sent successfully:", result["result"]["message_id"])


def main():
    download_font()
    prices = fetch_prices()
    print("Prices:", prices)
    img = build_image(prices)
    send_to_telegram(img)


if __name__ == "__main__":
    main()
