import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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


async def show_governorate_placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gov_name = query.data.replace("gov_", "")
    await query.edit_message_text(
        f"📍 محافظة {gov_name}\n\nقاعدة بيانات المحلات هتتضاف قريباً في هذه المحافظة."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_governorates, pattern="^shops_menu$"))
    app.add_handler(CallbackQueryHandler(show_governorate_placeholder, pattern="^gov_"))
    app.run_polling()


if __name__ == "__main__":
    main()
