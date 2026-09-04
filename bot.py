import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
    ConversationHandler,
)

from database import (
    init_db, get_cities, get_shop_by_id, count_shops,
    get_pending_shops, count_pending_shops, update_shop_status,
    get_shops_paginated, search_shops_paginated, add_shop,
)
from seed_data import seed
from import_csv import import_from_csv
from ai_extract import extract_shop_data

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

ADD_NAME, ADD_GOV, ADD_CITY, ADD_ADDRESS, ADD_PHONE, ADD_WHATSAPP = range(6)


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 محلات وتجار الذهب في مصر", callback_data="shops_menu")],
        [InlineKeyboardButton("🔎 البحث عن محل ذهب", callback_data="search_start")],
        [InlineKeyboardButton("➕ أضف محلك", callback_data="add_shop_start")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بيك في بوت الذهب 🟡\nاختر من القائمة:",
        reply_markup=main_menu_keyboard(),
    )


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "أهلاً بيك في بوت الذهب 🟡\nاختر من القائمة:",
        reply_markup=main_menu_keyboard(),
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

    buttons = [[InlineKeyboardButton(f"🏙 {c}", callback_data=f"city_{gov_name}|{c}|0")] for c in cities]
    buttons.append([InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="shops_menu")])
    await query.edit_message_text(
        f"📍 محافظة {gov_name}\nاختر المدينة/المركز:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_shops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gov_name, city_name, page_str = query.data.replace("city_", "").split("|")
    page = int(page_str)

    shops, total_pages = get_shops_paginated(gov_name, city_name, page)

    if not shops:
        await query.edit_message_text(
            "مفيش محلات متاحة هنا حالياً.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 رجوع", callback_data=f"gov_{gov_name}")]]
            ),
        )
        return

    buttons = [[InlineKeyboardButton(f"💍 {s['shop_name']}", callback_data=f"shop_{s['id']}")] for s in shops]

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"city_{gov_name}|{city_name}|{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f"city_{gov_name}|{city_name}|{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"gov_{gov_name}")])

    page_info = f" (صفحة {page+1}/{total_pages})" if total_pages > 1 else ""
    await query.edit_message_text(
        f"🏙 {city_name} - {gov_name}\nمحلات الذهب المتاحة:{page_info}",
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
    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_search"] = True
    await query.edit_message_text("🔎 اكتب اسم المحل أو اسم المنطقة اللي عايز تدور عليها:")


async def show_search_results(message_obj, keyword, page, context, edit=False):
    results, total_pages = search_shops_paginated(keyword, page)

    if not results:
        text = f"مفيش نتائج لـ \"{keyword}\"."
        buttons = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]]
        if edit:
            await message_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    buttons = [[InlineKeyboardButton(f"💍 {s['shop_name']} - {s['city']}", callback_data=f"shop_{s['id']}")] for s in results]

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"searchpage_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f"searchpage_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])

    page_info = f" (صفحة {page+1}/{total_pages})" if total_pages > 1 else ""
    text = f"نتائج البحث عن \"{keyword}\"{page_info}:"

    if edit:
        await message_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def addtext_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["awaiting_raw_text"] = True
    await update.message.reply_text(
        "🤖 ابعت النص غير المنظم اللي بيوصف المحل (زي: \"مجوهرات أحمد - شارع الجمهورية - الفيوم - 01012345678\")\n\n"
        "الذكاء الاصطناعي هيحاول يستخرج البيانات منه تلقائياً."
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_raw_text"):
        context.user_data["awaiting_raw_text"] = False
        raw_text = update.message.text.strip()
        await update.message.reply_text("⏳ جاري تحليل النص بالذكاء الاصطناعي...")

        try:
            extracted = extract_shop_data(raw_text)
        except Exception as e:
            await update.message.reply_text(f"حصل خطأ أثناء التحليل: {e}")
            return

        if not extracted.get("shop_name"):
            await update.message.reply_text(
                "❌ مقدرش أستخرج اسم محل واضح من النص ده. جرب تاني بنص أوضح أو استخدم /addtext."
            )
            return

        context.user_data["extracted_shop"] = extracted
        text = (
            "🤖 البيانات المستخرجة:\n\n"
            f"💍 الاسم: {extracted.get('shop_name') or '—'}\n"
            f"📍 المحافظة: {extracted.get('governorate') or '—'}\n"
            f"🏙 المدينة: {extracted.get('city') or '—'}\n"
            f"📌 العنوان: {extracted.get('address') or '—'}\n"
            f"📞 الهاتف: {extracted.get('phone') or '—'}\n"
            f"💬 واتساب: {extracted.get('whatsapp') or '—'}\n\n"
            "صح البيانات دي؟"
        )
        buttons = [[
            InlineKeyboardButton("✅ تأكيد وإضافة", callback_data="raw_confirm"),
            InlineKeyboardButton("❌ إلغاء", callback_data="raw_cancel"),
        ]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if not context.user_data.get("awaiting_search"):
        return
    context.user_data["awaiting_search"] = False
    keyword = update.message.text.strip()
    context.user_data["last_search"] = keyword
    await show_search_results(update.message, keyword, 0, context)


async def raw_text_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("مش مسموح لك.", show_alert=True)
        return
    await query.answer()

    extracted = context.user_data.get("extracted_shop")
    if not extracted:
        await query.edit_message_text("انتهت صلاحية العملية، جرب /addtext تاني.")
        return

    add_shop(
        shop_name=extracted.get("shop_name", ""),
        governorate=extracted.get("governorate", ""),
        city=extracted.get("city", ""),
        address=extracted.get("address", ""),
        phone=extracted.get("phone", ""),
        whatsapp=extracted.get("whatsapp", ""),
        source_url="مستخرج بالذكاء الاصطناعي من نص خام",
        status="Needs Review",
    )
    context.user_data["extracted_shop"] = None
    await query.edit_message_text("✅ تم إضافة المحل بنجاح. راجعه بالأمر /admin")


async def raw_text_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["extracted_shop"] = None
    await query.edit_message_text("تم الإلغاء.")


async def search_page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("searchpage_", ""))
    keyword = context.user_data.get("last_search", "")
    await show_search_results(query, keyword, page, context, edit=True)


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
    if shop["notes"]:
        text += f"\n\n📝 ملاحظات: {shop['notes']}"

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


async def add_shop_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["new_shop"] = {}
    await query.edit_message_text("➕ إضافة محلك\n\nاكتب اسم المحل:")
    return ADD_NAME


async def add_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop"]["shop_name"] = update.message.text.strip()
    buttons = []
    row = []
    for i, gov in enumerate(GOVERNORATES, 1):
        row.append(InlineKeyboardButton(gov, callback_data=f"addgov_{gov}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await update.message.reply_text(
        "اختر المحافظة:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ADD_GOV


async def add_shop_gov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    gov = query.data.replace("addgov_", "")
    context.user_data["new_shop"]["governorate"] = gov
    await query.edit_message_text(f"المحافظة: {gov}\n\nاكتب اسم المدينة أو المركز:")
    return ADD_CITY


async def add_shop_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop"]["city"] = update.message.text.strip()
    await update.message.reply_text("اكتب عنوان المحل بالتفصيل:")
    return ADD_ADDRESS


async def add_shop_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop"]["address"] = update.message.text.strip()
    await update.message.reply_text("اكتب رقم الهاتف:")
    return ADD_PHONE


async def add_shop_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop"]["phone"] = update.message.text.strip()
    await update.message.reply_text("اكتب رقم الواتساب (أو اكتب لا يوجد لو مفيش):")
    return ADD_WHATSAPP


async def add_shop_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whatsapp_text = update.message.text.strip()
    whatsapp = "" if whatsapp_text in ("لا يوجد", "-", "لا") else whatsapp_text

    data = context.user_data["new_shop"]
    add_shop(
        shop_name=data["shop_name"],
        governorate=data["governorate"],
        city=data["city"],
        address=data["address"],
        phone=data["phone"],
        whatsapp=whatsapp,
        source_url="أضيف عن طريق صاحب المحل",
        status="Needs Review",
    )
    context.user_data["new_shop"] = {}
    await update.message.reply_text(
        "✅ تم استلام بيانات محلك بنجاح، وهيتم مراجعتها والتأكد منها قريباً.\nشكراً لك 🙏",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def add_shop_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_shop"] = {}
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def main():
    init_db()
    if count_shops() == 0:
        seed()

    app = Application.builder().token(BOT_TOKEN).build()

    add_shop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_shop_start, pattern="^add_shop_start$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shop_name)],
            ADD_GOV: [CallbackQueryHandler(add_shop_gov, pattern="^addgov_")],
            ADD_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shop_city)],
            ADD_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shop_address)],
            ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shop_phone)],
            ADD_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shop_whatsapp)],
        },
        fallbacks=[CommandHandler("cancel", add_shop_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addtext", addtext_start))
    app.add_handler(add_shop_conv)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_csv_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(CallbackQueryHandler(show_governorates, pattern="^shops_menu$"))
    app.add_handler(CallbackQueryHandler(show_cities, pattern="^gov_"))
    app.add_handler(CallbackQueryHandler(show_shops, pattern="^city_"))
    app.add_handler(CallbackQueryHandler(search_start, pattern="^search_start$"))
    app.add_handler(CallbackQueryHandler(search_page_nav, pattern="^searchpage_"))
    app.add_handler(CallbackQueryHandler(raw_text_confirm, pattern="^raw_confirm$"))
    app.add_handler(CallbackQueryHandler(raw_text_cancel, pattern="^raw_cancel$"))
    app.add_handler(CallbackQueryHandler(back_to_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(show_shop_details, pattern="^shop_"))
    app.run_polling()


if __name__ == "__main__":
    main()
