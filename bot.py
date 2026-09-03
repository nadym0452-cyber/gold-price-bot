import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# استدعاء دالة إنشاء قاعدة البيانات والدالة التجريبية
from database import init_db, DB_NAME
from seed_data import seed_fayoum_data

# إعداد السجلات (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# المحافظات المتاحة حالياً
GOVERNORATES = [
    "الفيوم", "القاهرة", "الجيزة", "الإسكندرية", "الدقهلية",
    "الشرقية", "القليوبية", "الغربية", "المنوفية", "البحيرة",
    "كفر الشيخ", "دمياط", "بورسعيد", "الإسماعيلية", "السويس",
    "شمال سيناء", "جنوب سيناء", "بني سويف", "المنيا", "أسيوط",
    "سوهاج", "قنا", "الأقصر", "أسوان", "البحر الأحمر", "الوادي الجديد", "مطروح"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏪 محلات وتجار الذهب في مصر", callback_data="show_govs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "أهلاً بك في بوت أسعار ودليل محلات الذهب في مصر 🇪🇬\nاختر من القائمة أدناه:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "show_govs":
        # عرض قائمة المحافظات الـ 27
        keyboard = []
        row = []
        for gov in GOVERNORATES:
            row.append(InlineKeyboardButton(gov, callback_data=f"gov_{gov}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر المحافظة:", reply_markup=reply_markup)

    elif data.startswith("gov_"):
        gov_name = data.replace("gov_", "")
        
        # البحث عن المدن التابعة للمحافظة من قاعدة البيانات
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM shops WHERE governorate = ? AND status = 'Verified'", (gov_name,))
        cities = cursor.fetchall()
        conn.close()

        if not cities:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="show_govs")]]
            await query.edit_message_text(
                f"عفواً، لا توجد محلات مسجلة حالياً في محافظة **{gov_name}**.\nجرب اختيار **الفيوم** لرؤية البيانات التجريبية.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return

        keyboard = []
        for city_tuple in cities:
            city = city_tuple[0]
            keyboard.append([InlineKeyboardButton(f"📍 {city}", callback_data=f"city_{gov_name}_{city}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="show_govs")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"محافظة {gov_name} - اختر المدينة/المركز:", reply_markup=reply_markup)

    elif data.startswith("city_"):
        _, gov_name, city_name = data.split("_", 2)

        # جلب المحلات المعتمدة فقط في هذه المدينة
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT shop_name, phone, address, maps_url FROM shops WHERE governorate = ? AND city = ? AND status = 'Verified'",
            (gov_name, city_name)
        )
        shops = cursor.fetchall()
        conn.close()

        text = f"🏪 **محلات الذهب في {city_name} ({gov_name}):**\n\n"
        for shop in shops:
            name, phone, address, maps_url = shop
            text += f"🔹 **{name}**\n"
            text += f"📞 هاتف: `{phone}`\n"
            text += f"📍 العنوان: {address}\n"
            if maps_url:
                text += f"🗺️ [رابط الموقع على الخريطة]({maps_url})\n"
            text += "━━━\n"

        keyboard = [[InlineKeyboardButton("🔙 رجوع للمحافظات", callback_data="show_govs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("خطأ: لم يتم العثور على BOT_TOKEN في المتغيرات البيئية!")
        return

    # 1. إنشاء الجدول إن لم يكن موجوداً
    init_db()
    
    # 2. إضافة البيانات التجريبية لمحافظة الفيوم
    seed_fayoum_data()

    # 3. تشغيل البوت
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
