# -*- coding: utf-8 -*-
"""
Telegram Sales Bot for KorpusM (Мариуполь) with SQLite Lead Storage & WebApp
Канал: @mebelmariupoll
Телефон мастера: +7 (949) 710-52-78

Функционал:
- Квалификация входящих лидов 24/7 (кухни, шкафы, торговая мебель)
- Экспресс-калькулятор стоимости
- Приём фото и эскизов помещения
- Запись на замер по районам Мариуполя
- Сохранение заявок в локальную базу SQLite
- Команда /leads для мастера (просмотр свежих заявок прямо в боте)
- Мгновенная отправка готовой анкеты мастеру в Telegram
"""

import os
import sqlite3
import datetime
import logging
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8859368248:AAEnH9_tTEMnoHK5dNvwNfB9IYiyMEkU3Oo")
MASTER_CHAT_ID = os.getenv("MASTER_CHAT_ID", "YOUR_CHAT_ID")
PHONE_NUMBER = "+7 (949) 710-52-78"
TG_CHANNEL = "https://t.me/mebelmariupoll"
DB_PATH = os.path.join(os.path.dirname(__file__), "leads.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = TeleBot(BOT_TOKEN)

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        client_name TEXT,
        username TEXT,
        phone TEXT,
        district TEXT,
        item_type TEXT,
        length REAL,
        material TEXT,
        estimate INTEGER,
        has_photo INTEGER,
        status TEXT DEFAULT 'Новая'
    )''')
    conn.commit()
    conn.close()

init_db()

# Session state store
user_sessions = {}

# Prices reference per linear meter
BASE_PRICES = {
    "kitchen": {"name": "Кухня на заказ", "base": 45000},
    "wardrobe": {"name": "Шкаф-купе / Гардеробная", "base": 32000},
    "dressing": {"name": "Гардеробная комната", "base": 28000},
    "commercial": {"name": "Мебель для кафе / Магазина", "base": 38000},
    "other": {"name": "Индивидуальный проект", "base": 35000}
}

MATERIALS = {
    "ldsp": {"name": "ЛДСП Egger / Kronospan", "coef": 1.0},
    "mdf_film": {"name": "МДФ в плёнке ПВХ (софт-тач)", "coef": 1.3},
    "mdf_paint": {"name": "МДФ Эмаль (покраска по RAL)", "coef": 1.6},
    "premium": {"name": "Стекло в черном профиле / Шпон", "coef": 1.8}
}

DISTRICTS = [
    "Центральный", "Приморский", "Ильичевский", "Левобережный", "Пригород Мариуполя"
]


def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🪚 Рассчитать стоимость мебели", callback_data="calc_start"),
        types.InlineKeyboardButton("📸 Реальные работы мастера Евгения", callback_data="portfolio_show"),
        types.InlineKeyboardButton("⭐ Реальные отзывы заказчиков", callback_data="reviews_show"),
        types.InlineKeyboardButton("📐 Записаться на бесплатный замер", callback_data="measure_start"),
        types.InlineKeyboardButton("🏬 Мебель для бизнеса / Кафе / Магазинов", callback_data="commercial_info"),
        types.InlineKeyboardButton("💬 Написать мастеру в Telegram", url=TG_CHANNEL),
        types.InlineKeyboardButton("📞 Позвонить мастеру: " + PHONE_NUMBER, callback_data="show_phone")
    )
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {}
    
    text = (
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        "Вас приветствует мебельное производство **«KorpusM» (г. Мариуполь)**.\n\n"
        "Мы проектируем и изготавливаем корпусную мебель по индивидуальным размерам:\n"
        "✦ Кухни любой сложности\n"
        "✦ Встроенные шкафы-купе и гардеробные\n"
        "✦ Мебель для офисов, кафе и торговых магазинов\n\n"
        "📍 **Собственный цех в Мариуполе — честные цены без наценок салонов!**\n\n"
        "Выберите действие ниже, чтобы рассчитать примерную стоимость или вызвать мастера на бесплатный замер с образцами материалов:"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_menu())


@bot.message_handler(commands=['leads'])
def view_leads(message):
    """Команда для мастера: просмотр последних заявок из БД"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at, client_name, phone, item_type, estimate, district FROM leads ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📭 Заявок в базе пока нет.")
        return

    text = "📋 **Последние 5 заявок KorpusM:**\n\n"
    for r in rows:
        text += (
            f"🔹 **Заявка #{r[0]}** ({r[1]})\n"
            f"• Имя: {r[2]}\n"
            f"• Телефон: `{r[3]}`\n"
            f"• Изделие: {r[4]} ({r[6]})\n"
            f"• Оценка: {r[5]:,} ₽\n\n"
        )
    bot.reply_to(message, text.replace(",", " "), parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    data = call.data

    if data == "main_menu":
        bot.edit_message_text(
            "Главное меню **«KorpusM» Мариуполь**:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

    elif data == "show_phone":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            f"📞 Прямой контакт мастера KorpusM (Мариуполь):\n\n"
            f"**{PHONE_NUMBER}**\n\n"
            "Звоните или пишите в Telegram в любое удобное время!",
            parse_mode="Markdown"
        )


    elif data == "portfolio_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🍳 Кухни на заказ (фото проектов)", callback_data="port_kitchen"),
            types.InlineKeyboardButton("🚪 Шкафы и прихожие под потолок", callback_data="port_wardrobe"),
            types.InlineKeyboardButton("💡 Умные решения (бойлеры, подоконники)", callback_data="port_custom"),
            types.InlineKeyboardButton("☕ Мебель для кафе и бизнеса (STARCOFF)", callback_data="port_b2b"),
            types.InlineKeyboardButton("🎥 Видеообзоры с объектов (видео)", callback_data="port_videos"),
            types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
        )
        text = (
            """📸 *Живое портфолио мастера Евгения (KorpusM Мариуполь)*

В нашем архиве более 25 реальных объектов, 480+ фотографий и 7 видеообзоров.

Выберите интересующую категорию:"""
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "port_kitchen":
        bot.answer_callback_query(call.id)
        p1 = os.path.join(os.path.dirname(__file__), "portfolio", "01_kukhni", "kukhnya_uglovaya_grafit_2026-08-28", "photo_2026-08-28_22-52-44.jpg")
        p2 = os.path.join(os.path.dirname(__file__), "portfolio", "01_kukhni", "kukhnya_belyj_mat_gola_2026-08-28", "photo_2026-08-28_22-50-14.jpg")
        
        cap1 = """🍳 *Кухня «Графит & Дуб Натуральный»*
Угловой гарнитур под потолок, профиль Gola, влагостойкая столешница."""
        cap2 = """🍳 *Кухня «Белый мат Soft-Touch & LED»*
Интегрированная подсветка 4000K, встроенная бытовая техника."""
        
        if os.path.exists(p1):
            with open(p1, "rb") as f: bot.send_photo(chat_id, f, caption=cap1, parse_mode="Markdown")
        if os.path.exists(p2):
            with open(p2, "rb") as f: bot.send_photo(chat_id, f, caption=cap2, parse_mode="Markdown")
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪚 Рассчитать стоимость кухни", callback_data="type_kitchen"),
            types.InlineKeyboardButton("◀ Назад в портфолио", callback_data="portfolio_show")
        )
        bot.send_message(chat_id, "💡 Хотите рассчитать такую кухню под ваши размеры?", reply_markup=markup)

    elif data == "port_wardrobe":
        bot.answer_callback_query(call.id)
        p1 = os.path.join(os.path.dirname(__file__), "portfolio", "02_shkafy_i_prihozhie", "prihozhaya_pod_potolok_2026-03-23", "photo_2026-03-23_20-45-33.jpg")
        p2 = os.path.join(os.path.dirname(__file__), "portfolio", "02_shkafy_i_prihozhie", "shkaf_kupe_zerkalnyj_2026-03-23", "photo_2026-03-23_20-49-37.jpg")
        
        cap1 = """🚪 *Встроенная прихожая под потолок*
Ростовое зеркало, обувница, мягкое сиденье и скрытые вертикальные ручки."""
        cap2 = """🚪 *Зеркальный шкаф-купе в нишу*
Бесшумный ход раздвижной системы, пантографы и ящики полного выдвижения."""
        
        if os.path.exists(p1):
            with open(p1, "rb") as f: bot.send_photo(chat_id, f, caption=cap1, parse_mode="Markdown")
        if os.path.exists(p2):
            with open(p2, "rb") as f: bot.send_photo(chat_id, f, caption=cap2, parse_mode="Markdown")
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪚 Рассчитать шкаф / прихожую", callback_data="type_wardrobe"),
            types.InlineKeyboardButton("◀ Назад в портфолио", callback_data="portfolio_show")
        )
        bot.send_message(chat_id, "💡 Рассчитаем шкаф точно по размерам помещения?", reply_markup=markup)

    elif data == "port_custom":
        bot.answer_callback_query(call.id)
        p1 = os.path.join(os.path.dirname(__file__), "portfolio", "03_individualnye_resheniya", "shkaf_maskirovka_boylera_2025-12-16", "photo_2025-12-16_10-01-24.jpg")
        p2 = os.path.join(os.path.dirname(__file__), "portfolio", "03_individualnye_resheniya", "stol_podokonnik_dlya_laptop_2026-07-05", "photo_2026-07-05_18-39-49.jpg")
        
        cap1 = """💡 *Шкаф для маскировки бойлера в санузел*
Скрытый монтаж со свободным доступом к кранам.
TG: https://t.me/mebelmariupoll/13"""
        cap2 = """💡 *Стол-подоконник для рабочего места*
Превращение подоконника в удобный стол с ящиками.
TG: https://t.me/mebelmariupoll/16"""
        
        if os.path.exists(p1):
            with open(p1, "rb") as f: bot.send_photo(chat_id, f, caption=cap1, parse_mode="Markdown")
        if os.path.exists(p2):
            with open(p2, "rb") as f: bot.send_photo(chat_id, f, caption=cap2, parse_mode="Markdown")
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪚 Заказать индивидуальное решение", callback_data="type_other"),
            types.InlineKeyboardButton("◀ Назад в портфолио", callback_data="portfolio_show")
        )
        bot.send_message(chat_id, "💡 Изготовим нестандартную конструкцию любой сложности.", reply_markup=markup)

    elif data == "port_b2b":
        bot.answer_callback_query(call.id)
        p1 = os.path.join(os.path.dirname(__file__), "portfolio", "04_kommercheskaya_mebel", "cafe_starcoff_mariupol_2025-09-03", "photo_2025-09-03_18-35-40 (2).jpg")
        p2 = os.path.join(os.path.dirname(__file__), "portfolio", "04_kommercheskaya_mebel", "resepshn_i_priemnye_zony_2025-09-09", "photo_2025-09-09_00-33-17.jpg")
        
        cap1 = """☕ *Сеть кофеен «STARCOFF» (Мариуполь)*
Барная стойка бариста, столы из массива дуба, стеллажи.
TG: https://t.me/mebelmariupoll/5"""
        cap2 = """🏬 *Стойка ресепшн и торговая мебель*
Износостойкие материалы, скрытая разводка кабелей, подсветка."""
        
        if os.path.exists(p1):
            with open(p1, "rb") as f: bot.send_photo(chat_id, f, caption=cap1, parse_mode="Markdown")
        if os.path.exists(p2):
            with open(p2, "rb") as f: bot.send_photo(chat_id, f, caption=cap2, parse_mode="Markdown")
            
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📋 Рассчитать мебель для бизнеса", callback_data="type_commercial"),
            types.InlineKeyboardButton("◀ Назад в портфолио", callback_data="portfolio_show")
        )
        bot.send_message(chat_id, "💡 Работаем по безналичному расчету и договорам с юрлицами.", reply_markup=markup)

    elif data == "port_videos":
        bot.answer_callback_query(call.id)
        v1 = os.path.join(os.path.dirname(__file__), "portfolio", "05_video_obzory", "video_01_kukhnya_obzor_1034", "video_01_kukhnya_obzor_1034.mp4")
        v2 = os.path.join(os.path.dirname(__file__), "portfolio", "05_video_obzory", "video_03_shkaf_kupe_obzor_1840", "video_03_shkaf_kupe_obzor_1840.mp4")
        
        bot.send_message(chat_id, "🎥 Отправляю реальные видеообзоры установленной мебели в Мариуполе...")
        
        if os.path.exists(v1):
            with open(v1, "rb") as f:
                bot.send_video(chat_id, f, caption="🎥 Видеообзор кухонного гарнитура с доводчиками (Мариуполь)")
        if os.path.exists(v2):
            with open(v2, "rb") as f:
                bot.send_video(chat_id, f, caption="🎥 Видеообзор распашного шкафа под потолок")
                
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📐 Записаться на замер", callback_data="measure_start"),
            types.InlineKeyboardButton("📢 Смотреть все 7 видео в TG-канале", url=TG_CHANNEL),
            types.InlineKeyboardButton("◀ Назад в портфолио", callback_data="portfolio_show")
        )
        bot.send_message(chat_id, "💡 Хотите такую же качественную мебель? Запишитесь на бесплатный замер!", reply_markup=markup)

    elif data == "reviews_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪚 Рассчитать стоимость своего проекта", callback_data="calc_start"),
            types.InlineKeyboardButton("📐 Вызвать мастера на замер", callback_data="measure_start"),
            types.InlineKeyboardButton("📢 Смотреть канал @mebelmariupoll", url=TG_CHANNEL),
            types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
        )
        text = (
            "⭐ **Реальные отзывы заказчиков KorpusM (г. Мариуполь)**\n\n"
            "☕ **Сеть кофеен «STARCOFF» (B2B / HoReCa):**\n"
            "«Огромное спасибо Евгению за барную стойку и столы из массива дуба. Поток гостей постоянный, но всё стоит монолитно, дерево обработано на высшем уровне!»\n"
            "🔗 Пост в TG: https://t.me/mebelmariupoll/5\n\n"
            "🚪 **Александр В. (Приморский район):**\n"
            "«Долго не знали, как спрятать 80-литровый бойлер в санузле. Евгений предложил скрытые фасады под плитку — теперь санузел просторный и доступ к кранам идеальный.»\n"
            "🔗 Пост в TG: https://t.me/mebelmariupoll/13\n\n"
            "💻 **Ольга К. (пр-т Металлургов):**\n"
            "«Хотелось сэкономить место и сделать из подоконника рабочий стол для ноутбука. Получилось удобное светлое место с выдвижными ящиками. Сделано точно и в срок!»\n"
            "🔗 Пост в TG: https://t.me/mebelmariupoll/16\n\n"
            "🍳 **Семья Денисовых (ЖК Мариуполь):**\n"
            "«Кухня до потолка с профилем Gola и подсветкой. Зазоры везде по 2 мм, доводчики бесшумные. Собрали за 1 день без пыли и грязи!»"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)

    elif data == "commercial_info":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📋 Рассчитать B2B-проект", callback_data="type_commercial"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = (
            "🏬 **Мебель для бизнеса и HoReCa в Мариуполе**\n\n"
            "Изготавливаем торговое оборудование и мебель высокой износостойкости:\n"
            "• Стойки ресепшн и барные стойки\n"
            "• Витрины, стеллажи и островные конструкции для магазинов\n"
            "• Столы и посадочные зоны для кафе/ресторанов\n"
            "• Рабочие места и кабинеты для офисов\n\n"
            "Работаем по безналичному расчету и с физлицами. Сроки — от 7 дней."
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "calc_start":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🍳 Кухня на заказ", callback_data="type_kitchen"),
            types.InlineKeyboardButton("🚪 Шкаф-купе / Распашной", callback_data="type_wardrobe"),
            types.InlineKeyboardButton("👗 Гардеробная комната", callback_data="type_dressing"),
            types.InlineKeyboardButton("🏬 Мебель для магазина / Кафе", callback_data="type_commercial"),
            types.InlineKeyboardButton("💡 Другое изделие", callback_data="type_other"),
            types.InlineKeyboardButton("◀ Отмена", callback_data="main_menu")
        )
        bot.edit_message_text(
            "**Шаг 1 из 4: Что вы планируете заказать?**",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data.startswith("type_"):
        ftype = data.replace("type_", "")
        user_sessions[chat_id]["type"] = ftype
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("до 2.0 метров", callback_data="len_2.0"),
            types.InlineKeyboardButton("2.5 метра", callback_data="len_2.5"),
            types.InlineKeyboardButton("3.0 метра", callback_data="len_3.0"),
            types.InlineKeyboardButton("3.5 метра", callback_data="len_3.5"),
            types.InlineKeyboardButton("4.0+ метра", callback_data="len_4.0"),
            types.InlineKeyboardButton("Не знаю / нужен замер", callback_data="len_3.0")
        )
        markup.add(types.InlineKeyboardButton("◀ Назад", callback_data="calc_start"))

        typeName = BASE_PRICES.get(ftype, {}).get("name", "Изделие")
        bot.edit_message_text(
            f"Выбрано: **{typeName}**\n\n"
            "**Шаг 2 из 4: Укажите примерную длину (погонные метры):**",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data.startswith("len_"):
        flen = float(data.replace("len_", ""))
        user_sessions[chat_id]["length"] = flen

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪵 ЛДСП Egger/Kronospan (Практично)", callback_data="mat_ldsp"),
            types.InlineKeyboardButton("🎨 МДФ в плёнке ПВХ (Софт-тач, фрезеровка)", callback_data="mat_mdf_film"),
            types.InlineKeyboardButton("✨ МДФ Эмаль (Покраска в любой цвет)", callback_data="mat_mdf_paint"),
            types.InlineKeyboardButton("💎 Стекло в профиле / Шпон (Премиум)", callback_data="mat_premium"),
            types.InlineKeyboardButton("◀ Назад", callback_data=f"type_{user_sessions[chat_id].get('type', 'kitchen')}")
        )
        bot.edit_message_text(
            f"Длина: **{flen} м**\n\n"
            "**Шаг 3 из 4: Какой материал фасадов предпочитаете?**",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data.startswith("mat_"):
        fmat = data.replace("mat_", "")
        user_sessions[chat_id]["material"] = fmat

        # Calculate preliminary price
        stype = user_sessions[chat_id].get("type", "kitchen")
        slen = user_sessions[chat_id].get("length", 3.0)
        base = BASE_PRICES.get(stype, {}).get("base", 40000)
        coef = MATERIALS.get(fmat, {}).get("coef", 1.0)
        
        calc_total = int(base * slen * coef)
        user_sessions[chat_id]["estimate"] = calc_total

        mat_name = MATERIALS.get(fmat, {}).get("name", "Стандарт")
        type_name = BASE_PRICES.get(stype, {}).get("name", "Мебель")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📸 Прикрепить фото/эскиз помещения", callback_data="send_photo_step"),
            types.InlineKeyboardButton("📐 Записаться на бесплатный замер", callback_data="measure_start"),
            types.InlineKeyboardButton("🔄 Пересчитать заново", callback_data="calc_start")
        )

        res_text = (
            "📊 **Результат предварительного расчёта:**\n\n"
            f"• Изделие: **{type_name}**\n"
            f"• Длина: **{slen} пог.м**\n"
            f"• Материал: **{mat_name}**\n\n"
            f"💰 **Ориентировочная стоимость:** от **{calc_total:,} ₽**\n\n"
            "_В стоимость входит: 3D-проект, выезд на замер по Мариуполю, раскрой, кромление, фурнитура с доводчиками, доставка и монтаж под ключ._\n\n"
            "Хотите отправить фото помещения/эскиз или записаться на бесплатный выезд замерщика с образцами?"
        )
        bot.edit_message_text(res_text.replace(",", " "), chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "send_photo_step":
        user_sessions[chat_id]["state"] = "awaiting_photo"
        bot.send_message(
            chat_id,
            "📸 Пожалуйста, отправьте фото комнаты, места под установку или готовый эскиз/картинку из интернета, которая вам нравится:"
        )

    elif data == "measure_start":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for dist in DISTRICTS:
            markup.add(types.InlineKeyboardButton(dist, callback_data=f"dist_{dist}"))
        markup.add(types.InlineKeyboardButton("◀ В меню", callback_data="main_menu"))

        bot.edit_message_text(
            "📍 **В каком районе Мариуполя планируется установка?**\n"
            "Мастер выезжает бесплатно с чемоданом образцов материалов:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data.startswith("dist_"):
        district = data.replace("dist_", "")
        user_sessions[chat_id]["district"] = district
        user_sessions[chat_id]["state"] = "awaiting_phone"

        bot.send_message(
            chat_id,
            f"Район: **{district}**\n\n"
            "Пожалуйста, напишите ваш **номер телефона (+7 949 ...)** и **имя**, чтобы мастер согласовал удобный день замера:",
            parse_mode="Markdown"
        )


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    file_id = message.photo[-1].file_id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    user_sessions[chat_id]["photo_file_id"] = file_id
    user_sessions[chat_id]["state"] = "awaiting_phone"

    bot.reply_to(
        message,
        "👍 Фото успешно получено!\n\n"
        "Теперь напишите ваш **номер телефона (+7 949 ...)** и **имя**, чтобы мастер сделал детальный расчёт по этому проекту:",
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda msg: user_sessions.get(msg.chat.id, {}).get("state") == "awaiting_phone")
def handle_contact_input(message):
    chat_id = message.chat.id
    session = user_sessions.get(chat_id, {})
    contact_text = message.text

    session["contact"] = contact_text
    session["username"] = message.from_user.username or "Не указан"
    session["first_name"] = message.from_user.first_name or "Клиент"

    # Save to SQLite Database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO leads 
            (created_at, client_name, username, phone, district, item_type, length, material, estimate, has_photo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                session['first_name'],
                session['username'],
                contact_text,
                session.get('district', 'Мариуполь'),
                BASE_PRICES.get(session.get('type', 'kitchen'), {}).get('name', 'Мебель'),
                session.get('length', 3.0),
                MATERIALS.get(session.get('material', 'ldsp'), {}).get('name', 'Стандарт'),
                session.get('estimate', 0),
                1 if "photo_file_id" in session else 0
            )
        )
        conn.commit()
        conn.close()
    except Exception as db_err:
        logging.error(f"Database error: {db_err}")

    # Forward to master / admin
    lead_summary = (
        "🚨 **НОВАЯ ЗАЯВКА НА МЕБЕЛЬ | KorpusM Мариуполь**\n\n"
        f"👤 Клиент: {session['first_name']} (@{session['username']})\n"
        f"📞 Контакты: `{contact_text}`\n"
        f"📍 Район: {session.get('district', 'Не указан')}\n"
        f"🪚 Изделие: {BASE_PRICES.get(session.get('type', 'kitchen'), {}).get('name', 'Мебель')}\n"
        f"📏 Длина: {session.get('length', '—')} м\n"
        f"🪵 Фасады: {MATERIALS.get(session.get('material', 'ldsp'), {}).get('name', 'Стандарт')}\n"
        f"💰 Оценка: {session.get('estimate', 'Индивидуально')} ₽\n"
    )

    if MASTER_CHAT_ID and MASTER_CHAT_ID != "YOUR_CHAT_ID":
        try:
            bot.send_message(MASTER_CHAT_ID, lead_summary, parse_mode="Markdown")
            if "photo_file_id" in session:
                bot.send_photo(MASTER_CHAT_ID, session["photo_file_id"], caption="Прикрепленное фото от клиента")
        except Exception as e:
            logging.error(f"Error notifying master: {e}")

    # Reply to client
    confirm_text = (
        "🎉 **Заявка успешно принята!**\n\n"
        f"Спасибо, {session['first_name']}. Мастер KorpusM свяжется с вами в течение 15 минут для уточнения деталей и согласования времени замера.\n\n"
        f"📞 Прямой телефон: **{PHONE_NUMBER}**\n"
        f"📢 Наш канал: @mebelmariupoll"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀ Вернуться в меню", callback_data="main_menu"))
    
    bot.send_message(chat_id, confirm_text, parse_mode="Markdown", reply_markup=markup)
    user_sessions[chat_id]["state"] = "done"


if __name__ == "__main__":
    print(f"🤖 Bot KorpusM Мариуполь запущен. Телефон мастера: {PHONE_NUMBER}")
    bot.infinity_polling()
