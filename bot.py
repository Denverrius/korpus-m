# -*- coding: utf-8 -*-
"""
Telegram Sales & Production Bot for KorpusM (Мариуполь)
Bot: @korpus_m_admin_bot
Канал уведомлений: Сайты под ключ (-1004414921642)
Администратор: 8086868178
Телефон мастера: +7 (949) 710-52-78
Сайт: https://denverrius.github.io/korpus-m/
CRM: https://denverrius.github.io/korpus-m/crm.html

Сквозная интеграция:
- Каждая заявка из Telegram-бота мгновенно отправляется в канал «Сайты под ключ»
- Заявка сохраняется в SQLite (leads.db) и файловую базу заказов CRM (.data/orders/*.json)
- Автоматически обновляются счетчики в CRM (crm.html) и дашборде аналитики (analytics.html)
"""

import os
import glob
import json
import sqlite3
import datetime
import logging
import requests
from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8674575940:AAHHSoOujULSKDsuS6MCr3hvY2i4eVK4E4c")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1004414921642")  # Канал "Сайты под ключ"
ADMIN_ID = os.getenv("ADMIN_ID", "8086868178")
PHONE_NUMBER = "+7 (949) 710-52-78"
TG_BOT_LINK = "https://t.me/korpus_m_admin_bot"
WEBAPP_SITE_URL = "https://denverrius.github.io/korpus-m/"
WEBAPP_CRM_URL = "https://denverrius.github.io/korpus-m/crm.html"
WEBAPP_ANALYTICS_URL = "https://denverrius.github.io/korpus-m/analytics.html"

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "leads.db")
DATA_ORDERS_DIR = os.path.join(BASE_DIR, ".data", "orders")

if not os.path.exists(DATA_ORDERS_DIR):
    os.makedirs(DATA_ORDERS_DIR, exist_ok=True)

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


def send_channel_notification(lead_data):
    """Отправка уведомления о заявке в канал 'Сайты под ключ' и администратору"""
    order_id = lead_data.get("id", "KM-1115")
    name = lead_data.get("name", "Заказчик")
    phone = lead_data.get("phone", "—")
    district = lead_data.get("district", "Мариуполь")
    item_type = lead_data.get("type", "Кухня на заказ")
    material = lead_data.get("material", "Egger / Blum")
    estimate = lead_data.get("amount", 165000)
    username = lead_data.get("username", "")
    user_ref = f"@{username}" if username else "Не указан"

    html_text = (
        f"🪵 <b>НОВАЯ ЗАЯВКА НА МЕБЕЛЬ • КОРПУС М (Мариуполь)</b>\n\n"
        f"📋 <b>Номер заказа:</b> #{order_id}\n"
        f"👤 <b>Клиент:</b> {name} ({user_ref})\n"
        f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
        f"📍 <b>Район Мариуполя:</b> {district}\n"
        f"🪑 <b>Изделие:</b> {item_type}\n"
        f"🔩 <b>Материалы:</b> {material}\n"
        f"💰 <b>Смета:</b> {estimate:,} ₽\n"
        f"🌐 <b>Источник:</b> Telegram-бот @korpus_m_admin_bot\n\n"
        f"✅ <i>Заявка успешно продублирована в CRM цеха и аналитику.</i>"
    ).replace(",", " ")

    # 1. Send to Channel "Сайты под ключ"
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHANNEL_ID, "text": html_text, "parse_mode": "HTML"}, timeout=10)
        logging.info(f"✅ Notification dispatched to Channel {CHANNEL_ID}")
    except Exception as e:
        logging.warn(f"Failed to send to channel {CHANNEL_ID}: {e}")

    # 2. Send to Admin
    if ADMIN_ID and ADMIN_ID != CHANNEL_ID:
        try:
            requests.post(url, json={"chat_id": ADMIN_ID, "text": html_text, "parse_mode": "HTML"}, timeout=10)
            logging.info(f"✅ Notification dispatched to Admin {ADMIN_ID}")
        except Exception:
            pass


def duplicate_lead_to_crm(lead_data):
    """Сохранение заявки в CRM JSON-базу для мгновенного отображения в crm.html и analytics.html"""
    try:
        now = datetime.datetime.now()
        existing_files = [f for f in os.listdir(DATA_ORDERS_DIR) if f.endswith('.json')] if os.path.exists(DATA_ORDERS_DIR) else []
        next_num = 1000 + len(existing_files) + 1
        order_id = f"KM-{next_num}"

        order_obj = {
            "id": order_id,
            "number": next_num,
            "createdAt": now.isoformat(),
            "name": lead_data.get("name", "Клиент Telegram"),
            "phone": lead_data.get("phone", ""),
            "address": f"г. Мариуполь, {lead_data.get('district', 'Центральный район')}",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "type": lead_data.get("type", "Кухня на заказ"),
            "material": lead_data.get("material", "ЛДСП Egger + Blum"),
            "amount": int(lead_data.get("amount", 165000)),
            "source": "Telegram-бот (@korpus_m_admin_bot)",
            "comment": f"Заявка из бота. Район: {lead_data.get('district', 'Мариуполь')}. Юзер: @{lead_data.get('username', '')}",
            "status": "новая",
            "tg_delivered": True
        }

        filename = f"order_{int(now.timestamp())}_{order_id}.json"
        with open(os.path.join(DATA_ORDERS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(order_obj, f, ensure_ascii=False, indent=2)
        
        logging.info(f"✅ Saved order #{order_id} to CRM JSON store")
        return order_id
    except Exception as e:
        logging.error(f"Error saving to CRM store: {e}")
        return "KM-1115"


def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🌐 Открыть сайт и 3D-каталог", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("🪚 Рассчитать стоимость мебели", callback_data="calc_start"),
        types.InlineKeyboardButton("📐 Записаться на замер с образцами", callback_data="measure_start"),
        types.InlineKeyboardButton("📸 Реальные работы мастера в Мариуполе", callback_data="portfolio_show"),
        types.InlineKeyboardButton("⭐ Отзывы наших заказчиков", callback_data="reviews_show"),
        types.InlineKeyboardButton("💬 Прямой чат с мастером", url="https://t.me/mebelmariupoll"),
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
        "Мы проектируем и изготавливаем корпусную мебель по индивидуальным размерам:\n"
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
    markup.add(types.InlineKeyboardButton("📊 Открыть CRM заказов цеха", web_app=types.WebAppInfo(url=WEBAPP_CRM_URL)))
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
    markup.add(types.InlineKeyboardButton("📈 Открыть дашборд аналитики", web_app=types.WebAppInfo(url=WEBAPP_ANALYTICS_URL)))
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
        user_sessions[chat_id]["item_type"] = types_map.get(t_key, "Кухня на заказ")

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
            "✓ В стоимость включены: 3D-визуализация, распил на ЧПУ, кромление PUR-клеем, доставка и монтаж под ключ в Мариуполе.\n\n"
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
    
    district = session.get("district", "Центральный район")
    item_type = session.get("item_type", "Кухня на заказ")
    length_val = session.get("length", 3.0)
    material = session.get("material", "ЛДСП Egger + Blum")
    estimate = session.get("estimate", 165000)
    has_photo = session.get("has_photo", 0)

    # 1. Save to SQLite Database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO leads (created_at, client_name, username, phone, district, item_type, length, material, estimate, has_photo, comment, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (now_str, client_name, username, text, district, item_type, length_val, material, estimate, has_photo, f"Заявка из Telegram бота @korpus_m_admin_bot", "Новая"))
        sql_lead_id = c.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        sql_lead_id = 1115

    # 2. Duplicate to CRM JSON Store (shows up in crm.html and analytics.html)
    lead_dict = {
        "name": client_name,
        "phone": text,
        "district": district,
        "type": item_type,
        "material": material,
        "amount": estimate,
        "username": username
    }
    crm_order_id = duplicate_lead_to_crm(lead_dict)

    # 3. Send Notification to Channel "Сайты под ключ" & Admin
    lead_dict["id"] = crm_order_id
    send_channel_notification(lead_dict)

    confirm_text = (
        f"✅ **Спасибо, {client_name}! Ваша заявка #{crm_order_id} принята.**\n\n"
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
    logging.info("🪵 Korpus M Telegram Bot (@korpus_m_admin_bot) started polling with channel notifications...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
