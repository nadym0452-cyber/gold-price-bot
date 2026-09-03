import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from database import init_db, get_cities, get_shops, get_shop_by_id, count_shops
from seed_data import seed

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]

GOVERNORATES = [
    "القاهرة", "الجيزة", "الإسكندرية", "الفيوم", "المنوفية", "الشرقية",
    "الدقهلية", "البحيرة", "الغربية", "كفر الشيخ", "دمياط", "بورسعيد",
    "الإسماعيلية", "السويس", "شمال سيناء", "جنوب سيناء", "بني سويف",
    "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "البحر الأحمر",
    "الوادي الجديد", "مطروح", "القليوبية",
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🏪 محلات وتجار الذهب في مصر", callback_data="shops_menu")]]
    await update.message.reply_text(
        "أهلاً بيك في بوت الذهب 🟡\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_governorates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = []
    row = []
    for i, gov in enumerate(GOVERNORATES, 1):
        row.append(InlineKeyboardButton(f"📍 {gov}", callback_data=f"gov_{gov}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await query.edit_message_text(
        "🇪🇬 اختر المحافظة التي تبحث فيها عن محلات وتجار الذهب:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gov_name = query.data.replace("gov_", "")
    cities = get_cities(gov_name)

    if not cities:
        await query.edit_message_text(
            f"📍 محافظة {gov_name}\n\nقاعدة بيانات المحلات هتتضاف قريباً في هذه المحافظة.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="shops_menu")]]
            ),
        )
        return

    buttons = [[InlineKeyboardButton(f"🏙 {c}", callback_data=f"city_{gov_name}|{c}")] for c in cities]
    buttons.append([InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="shops_menu")])
    await query.edit_message_text(
        f"📍 محافظة {gov_name}\nاختر المدينة/المركز:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gov_name, city_name = query.data.replace("city_", "").split("|")
    shops = get_shops(gov_name, city_name)

    if not shops:
        await query.edit_message_text("مفيش محلات متاحة هنا حالياً.")
        return

    buttons = [[InlineKeyboardButton(f"💍 {s['shop_name']}", callback_data=f"shop_{s['id']}")] for s in shops]
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"gov_{gov_name}")])
    await query.edit_message_text(
        f"🏙 {city_name} - {gov_name}\nمحلات الذهب المتاحة:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_shop_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    shop_id = int(query.data.replace("shop_", ""))
    shop = get_shop_by_id(shop_id)

    if not shop:
        await query.edit_message_text("المحل ده مش موجود.")
        return

    text = f"💍 {shop['shop_name']}\n📍 {shop['address']}\n📞 {shop['phone']}"

    buttons = []
    if shop["phone"]:
        buttons.append([InlineKeyboardButton("📞 اتصال", url=f"tel:{shop['phone']}")])
    if shop["whatsapp"]:
        buttons.append([InlineKeyboardButton("💬 واتساب", url=f"https://wa.me/{shop['whatsapp']}")])
    if shop["maps_url"]:
        buttons.append([InlineKeyboardButton("🗺 الموقع على الخريطة", url=shop["maps_url"])])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"city_{shop['governorate']}|{shop['city']}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


def main():
    init_db()
    if count_shops() == 0:
        seed()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_governorates, pattern="^shops_menu$"))
    app.add_handler(CallbackQueryHandler(show_cities, pattern="^gov_"))
    app.add_handler(CallbackQueryHandler(show_shops, pattern="^city_"))
    app.add_handler(CallbackQueryHandler(show_shop_details, pattern="^shop_"))
    app.run_polling()


if __name__ == "__main__":
    main()
