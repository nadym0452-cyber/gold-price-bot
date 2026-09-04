import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

from database import (
    init_db, get_cities, get_shops, get_shop_by_id, count_shops,
    get_pending_shops, count_pending_shops, update_shop_status,
)
from seed_data import seed
from import_csv import import_from_csv

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 8693924902

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

    text = f"💍 {shop['shop_name']}\n📍 {shop['address']}"
    if shop["phone"]:
        text += f"\n📱 للاتصال: {shop['phone']}"

    buttons = []
    if shop["whatsapp"]:
        buttons.append([InlineKeyboardButton("💬 واتساب", url=f"https://wa.me/{shop['whatsapp']}")])
    if shop["maps_url"]:
        buttons.append([InlineKeyboardButton("🗺 الموقع على الخريطة", url=shop["maps_url"])])
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"city_{shop['governorate']}|{shop['city']}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("مش مسموح لك بالوصول لده.")
        return
    await send_next_pending(update.message, context)


async def send_next_pending(message_obj, context: ContextTypes.DEFAULT_TYPE, edit=False):
    pending = get_pending_shops(limit=1)
    total = count_pending_shops()

    if not pending:
        text = "✅ مفيش محلات محتاجة مراجعة دلوقتي."
        if edit:
            await message_obj.edit_message_text(text)
        else:
            await message_obj.reply_text(text)
        return

    shop = pending[0]
    label = "⚠️ تكرار محتمل" if shop["status"] == "Possible Duplicate" else "📋 محتاج مراجعة"
    text = (
        f"{label} ({total} محل متبقي)\n\n"
        f"💍 {shop['shop_name']}\n"
        f"📍 المحافظة: {shop['governorate']}\n"
        f"🏙 المدينة: {shop['city']}\n"
        f"📌 العنوان: {shop['address'] or '—'}\n"
        f"📞 الهاتف: {shop['phone'] or '—'}\n"
        f"💬 واتساب: {shop['whatsapp'] or '—'}\n"
        f"🗺 الخريطة: {shop['maps_url'] or '—'}\n"
        f"🗂 المصدر: {shop['source_url'] or '—'}"
    )
    buttons = [[
        InlineKeyboardButton("✅ اعتماد", callback_data=f"admin_approve_{shop['id']}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{shop['id']}"),
    ]]

    if edit:
        await message_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("مش مسموح لك.", show_alert=True)
        return
    await query.answer()

    data = query.data
    if data.startswith("admin_approve_"):
        shop_id = int(data.replace("admin_approve_", ""))
        update_shop_status(shop_id, "Verified")
    elif data.startswith("admin_reject_"):
        shop_id = int(data.replace("admin_reject_", ""))
        update_shop_status(shop_id, "Invalid")

    await send_next_pending(query, context, edit=True)


async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    document = update.message.document
    if not document or not document.file_name.endswith(".csv"):
        await update.message.reply_text("من فضلك ابعت ملف بصيغة CSV.")
        return

    file = await document.get_file()
    local_path = "temp_import.csv"
    await file.download_to_drive(local_path)

    try:
        import_from_csv(local_path)
        await update.message.reply_text(
            "✅ تم استيراد الملف بنجاح.\nراجع المحلات الجديدة بالأمر /admin"
        )
    except Exception as e:
        await update.message.reply_text(f"حصل خطأ أثناء الاستيراد: {e}")


def main():
    init_db()
    if count_shops() == 0:
        seed()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv_upload))
    app.add_handler(CallbackQueryHandler(show_governorates, pattern="^shops_menu$"))
    app.add_handler(CallbackQueryHandler(show_cities, pattern="^gov_"))
    app.add_handler(CallbackQueryHandler(show_shops, pattern="^city_"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(show_shop_details, pattern="^shop_"))
    app.run_polling()


if __name__ == "__main__":
    main()
