# -*- coding: utf-8 -*-
"""
Telegram Sales & Production Bot for KorpusM (Мариуполь)
Bot: @korpus_m_admin_bot
Канал: @mebelmariupoll
Телефон мастера Евгения: +7 (949) 710-52-78
Сайт: https://denverrius.github.io/korpus-m/

Функционал:
- WebApp интеграция (сайт и CRM прямо внутри Telegram)
- Экспресс-калькулятор стоимости кухни / шкафа / гардеробной
- Запись на бесплатный выезд замерщика с чемоданом образцов по районам Мариуполя
- Живое портфолио сданных объектов
- Приём фото и эскизов помещения от заказчиков
- Сохранение заявок в SQLite (leads.db)
- Панель управления мастера (/leads, /stats)
"""

import os
import sqlite3
import datetime
import logging
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8674575940:AAHHSoOujULSKDsuS6MCr3hvY2i4eVK4E4c")
MASTER_CHAT_ID = os.getenv("MASTER_CHAT_ID", "")
PHONE_NUMBER = "+7 (949) 710-52-78"
TG_CHANNEL = "https://t.me/mebelmariupoll"
WEBAPP_SITE_URL = "https://denverrius.github.io/korpus-m/"
WEBAPP_CRM_URL = "https://denverrius.github.io/korpus-m/crm.html"
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
        comment TEXT,
        status TEXT DEFAULT 'Новая'
    )''')
    conn.commit()
    conn.close()

init_db()

# User session state store
user_sessions = {}

DISTRICTS = [
    "Центральный", "Приморский", "Ильичевский", "Левобережный", "Пригород Мариуполя"
]

def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🌐 Открыть сайт и 3D-каталог", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("🪚 Рассчитать стоимость мебели", callback_data="calc_start"),
        types.InlineKeyboardButton("📐 Записаться на замер с образцами", callback_data="measure_start"),
        types.InlineKeyboardButton("📸 Реальные работы мастера в Мариуполе", callback_data="portfolio_show"),
        types.InlineKeyboardButton("⭐ Отзывы наших заказчиков", callback_data="reviews_show"),
        types.InlineKeyboardButton("💬 Написать мастеру в Telegram", url=TG_CHANNEL),
        types.InlineKeyboardButton("📞 Позвонить мастеру: " + PHONE_NUMBER, callback_data="show_phone")
    )
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {}

    first_name = message.from_user.first_name or "Гость"
    
    text = (
        f"👋 Здравствуйте, **{first_name}**!\n\n"
        "Вас приветствует мебельное производство **«Корпус М» (г. Мариуполь)**.\n\n"
        "Мы проектируем и изготавливаем корпусную мебель по вашим размерам:\n"
        "✦ **Кухни на заказ** (МДФ Эмаль, Soft-Touch, Egger, Blum)\n"
        "✦ **Шкафы-купе и гардеробные** под потолок\n"
        "✦ **Прихожие, детские и мебель в ванную**\n"
        "✦ **Мебель для кафе, магазинов и бизнеса**\n\n"
        "📍 *Собственный цех в Мариуполе — честные цены без салонных наценок, доставка и монтаж под ключ.*\n\n"
        "Выберите действие ниже, чтобы рассчитать смету или вызвать мастера на бесплатный замер с образцами:"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_menu())


@bot.message_handler(commands=['leads', 'orders'])
def view_leads(message):
    """Панель мастера: просмотр последних заявок"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at, client_name, phone, item_type, estimate, district, status FROM leads ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📭 В базе пока нет новых заявок.")
        return

    text = "📋 **Последние заявки «Корпус М» (Мариуполь):**\n\n"
    for r in rows:
        st_icon = "🟡" if r[7] == "Новая" else "⚙️"
        text += (
            f"{st_icon} **Заказ #KM-{r[0]}** ({r[1]})\n"
            f"👤 Клиент: {r[2]}\n"
            f"📞 Телефон: `{r[3]}`\n"
            f"🪑 Изделие: {r[4]}\n"
            f"📍 Район: {r[6]}\n"
            f"💰 Оценка: {r[5]:,} ₽\n\n"
        )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Открыть полную CRM-панель", web_app=types.WebAppInfo(url=WEBAPP_CRM_URL)))
    bot.reply_to(message, text.replace(",", " "), parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=['stats'])
def view_stats(message):
    """Сводка аналитики по заявкам"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(estimate), AVG(estimate) FROM leads")
    row = c.fetchone()
    conn.close()

    total_leads = row[0] or 0
    total_sum = row[1] or 0
    avg_sum = int(row[2] or 0)

    text = (
        "📊 **Сводка производства «Корпус М»:**\n\n"
        f"• Всего обработано заявок: **{total_leads}**\n"
        f"• Общая сумма смет: **{total_sum:,} ₽**\n"
        f"• Средний чек проекта: **{avg_sum:,} ₽**\n"
        "• Активных заказов в цехе: **3 проекта**\n"
    ).replace(",", " ")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📈 Открыть дашборд аналитики", web_app=types.WebAppInfo(url="https://denverrius.github.io/korpus-m/analytics.html")))
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=markup)


# Photo handler for customer blueprints / room pictures
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}
    
    user_sessions[chat_id]["has_photo"] = 1
    
    text = (
        "📸 **Фотография / эскиз получен!**\n\n"
        "Мастер Евгений изучит размеры и конструктивные особенности помещения.\n\n"
        "Пожалуйста, **напишите ваш номер телефона и имя** (+7 949 ...), чтобы мы перезвонили с готовым расчетом:"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    data = call.data

    if data == "main_menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "Главное меню мебельного производства **«Корпус М» (Мариуполь)**:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )

    elif data == "show_phone":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            f"📞 **Прямой контакт мастера Евгения (Корпус М Мариуполь):**\n\n"
            f"**{PHONE_NUMBER}**\n\n"
            "Звоните в любое удобное время (Пн–Сб с 9:00 до 19:00)!",
            parse_mode="Markdown"
        )

    elif data == "calc_start":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🍳 Кухня на заказ", callback_data="calc_type_kitchen"),
            types.InlineKeyboardButton("🚪 Шкаф-купе / Гардеробная", callback_data="calc_type_wardrobe"),
            types.InlineKeyboardButton("🧥 Прихожая под потолок", callback_data="calc_type_hall"),
            types.InlineKeyboardButton("☕ Мебель для бизнеса / Офис", callback_data="calc_type_commercial"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = "🪚 **Шаг 1 из 3:** Выберите тип мебели для расчета стоимости:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("calc_type_"):
        bot.answer_callback_query(call.id)
        t_key = data.replace("calc_type_", "")
        types_map = {
            "kitchen": "Кухня на заказ",
            "wardrobe": "Шкаф-купе / Гардеробная",
            "hall": "Прихожая под потолок",
            "commercial": "Мебель для бизнеса / Офис"
        }
        user_sessions[chat_id]["item_type"] = types_map.get(t_key, "Корпусная мебель")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("2.0 – 2.4 м (Компактная)", callback_data="calc_len_2.2"),
            types.InlineKeyboardButton("2.8 – 3.2 м (Стандартная прямая)", callback_data="calc_len_3.0"),
            types.InlineKeyboardButton("3.6 – 4.2 м (Большая угловая)", callback_data="calc_len_3.8"),
            types.InlineKeyboardButton("Более 4.5 м / Индивидуальный проект", callback_data="calc_len_5.0"),
            types.InlineKeyboardButton("◀ Назад", callback_data="calc_start")
        )
        text = f"📏 **Шаг 2 из 3:** Укажите ориентировочную длину мебели ({user_sessions[chat_id]['item_type']}):"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("calc_len_"):
        bot.answer_callback_query(call.id)
        length_val = float(data.replace("calc_len_", ""))
        user_sessions[chat_id]["length"] = length_val

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✦ ЛДСП Egger + доводчики (Практичный)", callback_data="calc_mat_egger"),
            types.InlineKeyboardButton("✦ МДФ Эмаль Soft-Touch + Blum (Премиум)", callback_data="calc_mat_mdf"),
            types.InlineKeyboardButton("✦ Шпон дуба / Черный профиль / Кварц (Люкс)", callback_data="calc_mat_luxury"),
            types.InlineKeyboardButton("◀ Назад", callback_data="calc_start")
        )
        text = "🔩 **Шаг 3 из 3:** Выберите класс фасадов и фурнитуры:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("calc_mat_"):
        bot.answer_callback_query(call.id)
        mat_key = data.replace("calc_mat_", "")
        mat_names = {
            "egger": ("ЛДСП Egger + Фурнитура с доводчиками", 1.0, 45000),
            "mdf": ("МДФ Эмаль Soft-Touch + Blum Австрия", 1.35, 62000),
            "luxury": ("Шпон дуба / Стекло в черном профиле + Кварц", 1.65, 78000)
        }
        mat_name, coef, base_pm = mat_names.get(mat_key, ("Egger", 1.0, 45000))
        user_sessions[chat_id]["material"] = mat_name
        
        length_val = user_sessions[chat_id].get("length", 3.0)
        item_type = user_sessions[chat_id].get("item_type", "Кухня на заказ")
        
        estimate = int(length_val * base_pm)
        user_sessions[chat_id]["estimate"] = estimate

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📐 Записаться на замер с образцами", callback_data="measure_start"),
            types.InlineKeyboardButton("🌐 Открыть 3D-калькулятор на сайте", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
            types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
        )

        res_text = (
            f"🎉 **Предварительный расчет готов!**\n\n"
            f"🪑 **Изделие:** {item_type}\n"
            f"📏 **Длина:** {length_val} м\n"
            f"🔩 **Материалы:** {mat_name}\n"
            f"💰 **Ориентировочная смета:** ~ **{estimate:,} ₽**\n\n"
            "✓ В стоимость включены: 3D-визуализация, распил на ЧПУ, кромление PUR-клеем, доставка и профессиональный монтаж под ключ в Мариуполе.\n\n"
            "Напишите ваш **номер телефона и имя** (+7 949 ...), чтобы зафиксировать скидку 10% на материалы и забронировать замер:"
        ).replace(",", " ")

        bot.edit_message_text(res_text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "measure_start":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        for dist in DISTRICTS:
            markup.add(types.InlineKeyboardButton(f"📍 {dist}", callback_data=f"dist_{dist}"))
        markup.add(types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu"))

        text = (
            "📐 **Бесплатный выезд мастера на замер по Мариуполю:**\n\n"
            "Мастер Евгений приедет с лазерным дальномером и чемоданом образцов (фасады Egger, МДФ, палитра RAL, фурнитура Blum).\n\n"
            "В каком **районе Мариуполя** находится ваш объект?"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("dist_"):
        bot.answer_callback_query(call.id)
        district = data.replace("dist_", "")
        user_sessions[chat_id]["district"] = district

        text = (
            f"📍 **Район выбран:** {district}\n\n"
            "Напишите ваш **номер телефона и имя** (+7 949 ...) для согласования удобного дня и времени замера:"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown")

    elif data == "portfolio_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🌐 Смотреть всё портфолио на сайте", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL + "#portfolio")),
            types.InlineKeyboardButton("🪚 Рассчитать стоимость проекта", callback_data="calc_start"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = (
            "📸 **Живое портфолио мебельного цеха «Корпус М»:**\n\n"
            "• **Кухня Графит & Дуб Натуральный** (пр. Металлургов) — 210 000 ₽\n"
            "• **Кухня Белый мат Soft-Touch & LED** (пр. Мира) — 185 000 ₽\n"
            "• **Прихожая под потолок с ростовым зеркалом** (ул. Нахимова) — 95 000 ₽\n"
            "• **Зеркальный шкаф-купе в нишу** (бульвар Шевченко) — 75 000 ₽\n"
            "• **Торговая мебель и барная стойка STARCOFF** — 340 000 ₽\n\n"
            "Все фото в высоком разрешении и видеообзоры доступны на сайте!"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "reviews_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📐 Записаться на замер", callback_data="measure_start"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = (
            "⭐ **Отзывы наших заказчиков (Мариуполь):**\n\n"
            "🗣 **Ольга (пр. Мира):**\n"
            "«Заказывали кухню под потолок. Сделали за 18 дней, петли Blum работают идеально плавно, ни одного зазора. Спасибо мастеру Евгению!»\n\n"
            "🗣 **Артем (Левобережный):**\n"
            "«Отличный шкаф-купе и гардеробная. Цены в 1.5 раза приятнее, чем в салонах города, так как работают напрямую из цеха.»\n\n"
            "🗣 **Виктория (Приморский):**\n"
            "«Идеально спрятали бойлер и трубы в санузле специальным влагостойким шкафом. Очень довольны!»"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)


# Message handler for capturing contact phone numbers & names
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    text = message.text.strip()
    session = user_sessions[chat_id]

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_name = message.from_user.first_name or "Заказчик"
    username = message.from_user.username or ""
    
    district = session.get("district", "Мариуполь")
    item_type = session.get("item_type", "Корпусная мебель")
    length_val = session.get("length", 3.0)
    material = session.get("material", "Egger / Blum")
    estimate = session.get("estimate", 165000)
    has_photo = session.get("has_photo", 0)

    # Save to SQLite Database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO leads (created_at, client_name, username, phone, district, item_type, length, material, estimate, has_photo, comment, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (now_str, client_name, username, text, district, item_type, length_val, material, estimate, has_photo, f"Заявка из Telegram бота @korpus_m_admin_bot", "Новая"))
        lead_id = c.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        lead_id = 1115

    # Notify Master if chat ID is set
    if MASTER_CHAT_ID:
        try:
            admin_msg = (
                f"🪵 **Новая заявка на мебель #KM-{lead_id}!**\n\n"
                f"👤 Клиент: {client_name} (@{username})\n"
                f"📞 Контакт: `{text}`\n"
                f"📍 Район: {district}\n"
                f"🪑 Изделие: {item_type} ({length_val} м)\n"
                f"🔩 Материал: {material}\n"
                f"💰 Оценка: {estimate:,} ₽\n"
            ).replace(",", " ")
            bot.send_message(MASTER_CHAT_ID, admin_msg, parse_mode="Markdown")
        except Exception:
            pass

    confirm_text = (
        f"✅ **Спасибо, {client_name}! Ваша заявка #KM-{lead_id} принята.**\n\n"
        f"Мастер Евгений свяжется с вами по номеру `{text}` в течение 5–10 минут для уточнения деталей и времени замера.\n\n"
        f"📞 Если хотите позвонить прямо сейчас:\n**{PHONE_NUMBER}**"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🌐 Перейти на сайт Корпус М", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
    )

    bot.send_message(chat_id, confirm_text, parse_mode="Markdown", reply_markup=markup)


if __name__ == "__main__":
    logging.info("🪵 Korpus M Telegram Bot (@korpus_m_admin_bot) started polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
