import os
import re
import io
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ---------- Settings ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SOURCE_URL = "https://www.gold-price-today.com/egypt/"

FONT_URL_REGULAR = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/noto-monthly-release-2025.12.01/fonts/NotoKufiArabic/hinted/ttf/NotoKufiArabic-Regular.ttf"
FONT_URL_BOLD = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/noto-monthly-release-2025.12.01/fonts/NotoKufiArabic/hinted/ttf/NotoKufiArabic-Bold.ttf"

FONT_REGULAR_PATH = "NotoKufiArabic-Regular.ttf"
FONT_BOLD_PATH = "NotoKufiArabic-Bold.ttf"

W, H = 1080, 1560
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


def ar(text):
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def clean_number(raw):
    digits = re.sub(r"[^\d]", "", raw)
    return f"{int(digits):,}"


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

    f_title = ImageFont.truetype(FONT_BOLD_PATH, 72)
    f_sub = ImageFont.truetype(FONT_BOLD_PATH, 40)
    f_label = ImageFont.truetype(FONT_BOLD_PATH, 46)
    f_price = ImageFont.truetype(FONT_BOLD_PATH, 66)
    f_small = ImageFont.truetype(FONT_REGULAR_PATH, 34)
    f_badge = ImageFont.truetype(FONT_BOLD_PATH, 50)

    def text_rtl(xy, text, font, fill, anchor="mm"):
        d.text(xy, ar(text), font=font, fill=fill, anchor=anchor)

    def rounded(box, radius=30, width=3):
        d.rounded_rectangle(box, radius=radius, outline=GOLD, width=width)

    margin = 40

    top_box = (margin, 40, W - margin, 190)
    rounded(top_box)
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    date_str = now.strftime("%Y/%m/%d")
    hour12 = now.strftime("%I:%M")
    ampm = "م" if now.strftime("%p") == "PM" else "ص"
    time_str = f"{hour12} {ampm}"

    d.line([(W // 2, 60), (W // 2, 170)], fill=GOLD, width=2)
    text_rtl((W - margin - 260, 115), date_str, f_sub, GOLD_LIGHT)
    text_rtl((margin + 260, 115), time_str, f_sub, GOLD_LIGHT)

    title_box = (margin, 230, W - margin, 430)
    rounded(title_box)
    text_rtl((W // 2, 300), "أسعار الذهب الآن", f_title, GOLD_LIGHT)
    text_rtl((W // 2 + 40, 385), "في مصر", f_sub, WHITE)
    flag_x0 = W // 2 - 160
    flag_w, flag_h = 70, 46
    flag_y0 = 385 - flag_h // 2
    stripe_h = flag_h // 3
    d.rectangle((flag_x0, flag_y0, flag_x0 + flag_w, flag_y0 + stripe_h), fill=(206, 17, 38))
    d.rectangle((flag_x0, flag_y0 + stripe_h, flag_x0 + flag_w, flag_y0 + 2 * stripe_h), fill=(255, 255, 255))
    d.rectangle((flag_x0, flag_y0 + 2 * stripe_h, flag_x0 + flag_w, flag_y0 + flag_h), fill=(0, 0, 0))

    row_h = 190
    gap = 24
    row_y = 470
    karats = [("24", "99.9"), ("21", "87.5"), ("18", "75.0")]

    for i, (k, purity) in enumerate(karats):
        y0 = row_y + i * (row_h + gap)
        y1 = y0 + row_h
        rounded((margin, y0, W - margin, y1))
        cy = (y0 + y1) // 2

        badge_cx = margin + 90
        d.rounded_rectangle(
            (badge_cx - 55, cy - 55, badge_cx + 55, cy + 55), radius=20, fill=GOLD
        )
        d.text((badge_cx, cy), k, font=f_badge, fill=(20, 15, 5), anchor="mm")

        text_rtl((W - margin - 160, cy - 30), f"عيار {k}", f_label, WHITE)
        text_rtl((W - margin - 160, cy + 30), f"نقاء {purity}%", f_small, GOLD)

        d.line([(W - margin - 320, y0 + 25), (W - margin - 320, y1 - 25)], fill=GOLD, width=2)

        price_cx = (margin + 200 + (W - margin - 340)) // 2
        text_rtl((price_cx, cy), f"{prices[k]} جنيه", f_price, GOLD_LIGHT)

    pound_y0 = row_y + 3 * (row_h + gap) + 10
    pound_y1 = pound_y0 + 210
    rounded((margin, pound_y0, W - margin, pound_y1))
    pcy = (pound_y0 + pound_y1) // 2
    text_rtl((W // 2, pcy - 45), "الجنيه الذهب", f_label, GOLD_LIGHT)
    text_rtl((W // 2, pcy + 40), f"{prices['pound']} جنيه", f_price, WHITE)

    footer_y0 = pound_y1 + 40
    footer_y1 = footer_y0 + 130
    rounded((margin, footer_y0, W - margin, footer_y1))
    fcy = (footer_y0 + footer_y1) // 2
    text_rtl((W // 2, fcy - 30), "الأسعار قابلة للتغيير على مدار اليوم", f_small, GOLD)
    text_rtl((W // 2, fcy + 30), "تحديث كل 15 دقيقة", f_small, GOLD)

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
    print("Telegram response:", resp.status_code, resp.text)
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
