# -*- coding: utf-8 -*-
"""
Telegram Sales & Production Bot for KorpusM (Мариуполь)
Bot: @korpus_m_admin_bot
Канал уведомлений: Сайты под ключ (-1004414921642)
Администратор: 8086868178
Телефон мастера: +7 (949) 710-52-78
Сайт: https://denverrius.github.io/korpus-m/
CRM: https://denverrius.github.io/korpus-m/crm.html
Аналитика: https://denverrius.github.io/korpus-m/analytics.html
"""

import os
import glob
import json
import html
import socket
import sqlite3
import datetime
import logging
import requests

# 1. PIN VERIFIED WORKING TELEGRAM GATEWAY (149.154.167.220)
_orig_getaddrinfo = socket.getaddrinfo

def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "api.telegram.org":
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
    responses = _orig_getaddrinfo(host, port, family, type, proto, flags)
    ipv4 = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else responses

socket.getaddrinfo = _custom_getaddrinfo

from telebot import TeleBot, types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8674575940:AAFICozyuZjPy0PNAOeR5hR7gTPgP4Q7gB0")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@saitypodkluch")

ADMIN_USERNAMES = {"den_dev82", "denver949", "denver_test", "illnass777", "maksim_rest", "den_dev", "denver"}
ADMIN_IDS = {"8086868178", str(os.getenv("ADMIN_ID", "8086868178"))}

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


def is_admin(user_id=None, username=None):
    """Проверка прав администратора по Telegram ID или юзернейму"""
    if user_id and str(user_id) in ADMIN_IDS:
        return True
    if username:
        clean_u = str(username).strip().lstrip('@').lower()
        if clean_u in ADMIN_USERNAMES:
            return True
    return False


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

user_sessions = {}

DISTRICTS = [
    "Центральный", "Приморский", "Ильичевский", "Левобережный", "Пригород Мариуполя"
]


def sync_lead_to_github_repo(order_obj):
    """Автоматическая синхронизация заказа с GitHub репозиторием Denverrius/korpus-m"""
    try:
        gh_token = os.getenv("GITHUB_TOKEN", "")
        repo = "Denverrius/korpus-m"
        file_path = "orders.json"
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "KorpusM-Telegram-Bot"
        }

        res = requests.get(url, headers=headers, timeout=10)
        current_orders = []
        file_sha = None

        if res.status_code == 200:
            data = res.json()
            file_sha = data.get("sha")
            content_b64 = data.get("content", "")
            import base64
            content_str = base64.b64decode(content_b64).decode("utf-8")
            current_orders = json.loads(content_str)
        
        current_orders.insert(0, order_obj)
        updated_content_str = json.dumps(current_orders, ensure_ascii=False, indent=2)
        import base64
        updated_content_b64 = base64.b64encode(updated_content_str.encode("utf-8")).decode("utf-8")

        commit_payload = {
            "message": f"feat: sync new lead #{order_obj.get('id', 'KM')} from @korpus_m_admin_bot",
            "content": updated_content_b64,
            "branch": "main"
        }
        if file_sha:
            commit_payload["sha"] = file_sha

        put_res = requests.put(url, headers=headers, json=commit_payload, timeout=15)
        if put_res.status_code in [200, 201]:
            logging.info(f"✅ Successfully committed order #{order_obj.get('id')} to GitHub repository!")
        else:
            logging.warn(f"GitHub commit status: {put_res.status_code}")
    except Exception as e:
        logging.error(f"Error syncing lead to GitHub: {e}")


def send_channel_notification(lead_data):
    """Отправка уведомления о заявке в канал 'Сайты под ключ' и администратору"""
    order_id = lead_data.get("id", "KM-1115")
    name = html.escape(str(lead_data.get("name", "Заказчик")))
    phone = html.escape(str(lead_data.get("phone", "—")))
    district = html.escape(str(lead_data.get("district", "Мариуполь")))
    item_type = html.escape(str(lead_data.get("type", "Кухня на заказ")))
    material = html.escape(str(lead_data.get("material", "Egger / Blum")))
    estimate = lead_data.get("amount", 165000)
    username = html.escape(str(lead_data.get("username", "")))
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
        f"✅ <i>Заявка автоматически поступила в CRM цеха и аналитику.</i>"
    ).replace(",", " ")

    # Send to Channel "Сайты под ключ"
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHANNEL_ID, "text": html_text, "parse_mode": "HTML"}, timeout=10)
        logging.info(f"✅ Notification dispatched to Channel {CHANNEL_ID}")
    except Exception as e:
        logging.warn(f"Failed to send to channel {CHANNEL_ID}: {e}")

    # Send to Admin
    for adm in ADMIN_IDS:
        try:
            requests.post(url, json={"chat_id": adm, "text": html_text, "parse_mode": "HTML"}, timeout=10)
        except Exception:
            pass


def duplicate_lead_to_crm(lead_data):
    """Сохранение заявки в CRM JSON-базу для мгновенного отображения в crm.html и analytics.html"""
    try:
        now = datetime.datetime.now()
        existing_files = [f for f in os.listdir(DATA_ORDERS_DIR) if f.endswith('.json')] if os.path.exists(DATA_ORDERS_DIR) else []
        next_num = 1210 + len(existing_files) + 1
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
        sync_lead_to_github_repo(order_obj)
        return order_id
    except Exception as e:
        logging.error(f"Error saving to CRM store: {e}")
        return "KM-1115"


def get_main_menu(user_is_admin=False):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if user_is_admin:
        markup.add(
            types.InlineKeyboardButton("👑 Панель Администратора", callback_data="admin_menu"),
            types.InlineKeyboardButton("📊 Вход в CRM-систему", url=WEBAPP_CRM_URL, web_app=types.WebAppInfo(url=WEBAPP_CRM_URL)),
            types.InlineKeyboardButton("📈 Вход в Аналитику", url=WEBAPP_ANALYTICS_URL, web_app=types.WebAppInfo(url=WEBAPP_ANALYTICS_URL))
        )
    markup.add(
        types.InlineKeyboardButton("🌐 Открыть сайт и 3D-каталог", url=WEBAPP_SITE_URL, web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("🪚 Рассчитать стоимость мебели", callback_data="calc_start"),
        types.InlineKeyboardButton("📐 Записаться на замер с образцами", callback_data="measure_start"),
        types.InlineKeyboardButton("📸 Реальные работы мастера в Мариуполе", callback_data="portfolio_show"),
        types.InlineKeyboardButton("⭐ Отзывы наших заказчиков", callback_data="reviews_show"),
        types.InlineKeyboardButton("💬 Прямой чат с мастером", url="https://t.me/Denver949"),
        types.InlineKeyboardButton("📞 Позвонить мастеру: " + PHONE_NUMBER, callback_data="show_phone")
    )
    return markup


def get_admin_keyboard():
    """Админская клавиатура с кнопками входа в CRM и Аналитику"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 Вход в CRM-систему", url=WEBAPP_CRM_URL, web_app=types.WebAppInfo(url=WEBAPP_CRM_URL)),
        types.InlineKeyboardButton("📈 Вход в Аналитику", url=WEBAPP_ANALYTICS_URL, web_app=types.WebAppInfo(url=WEBAPP_ANALYTICS_URL)),
        types.InlineKeyboardButton("📋 Свежие заявки из базы", callback_data="admin_recent_leads"),
        types.InlineKeyboardButton("💰 Сводка по производству", callback_data="admin_stats_summary"),
        types.InlineKeyboardButton("📢 Канал уведомлений @saitypodkluch", url="https://t.me/saitypodkluch"),
        types.InlineKeyboardButton("🌐 Открыть сайт KorpusM", url=WEBAPP_SITE_URL, web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("◀ Назад в главное меню", callback_data="main_menu")
    )
    return markup


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or ""
    user_sessions[chat_id] = {}

    first_name = html.escape(message.from_user.first_name or "Гость")
    user_is_admin = is_admin(user_id=user_id, username=username)

    logging.info(f"👋 /start by User: ID={user_id}, username=@{username}, name={first_name}, is_admin={user_is_admin}")
    
    text = (
        f"👋 Здравствуйте, <b>{first_name}</b>!\n\n"
        "Вас приветствует мебельное производство <b>«Корпус М» (г. Мариуполь)</b>.\n\n"
        "Мы проектируем и изготавливаем корпусную мебель по индивидуальным размерам:\n"
        "✦ <b>Кухни на заказ</b> (МДФ Эмаль, Soft-Touch, Egger, Blum)\n"
        "✦ <b>Шкафы-купе и гардеробные</b> под потолок\n"
        "✦ <b>Прихожие, детские и мебель в ванную</b>\n"
        "✦ <b>Мебель для кафе, магазинов и бизнеса</b>\n\n"
        "📍 <i>Собственный цех в Мариуполе — честные цены без салонных наценок, доставка и монтаж под ключ.</i>\n\n"
    )
    
    if user_is_admin:
        text += "👑 <b>ВЫ АВТОРИЗОВАНЫ КАК АДМИНИСТРАТОР</b>\nВам доступны разделы CRM-системы, аналитики и базы заявок.\n\n"

    text += "Выберите действие ниже:"
    
    try:
        # Send message with inline keyboard and remove any legacy persistent reply keyboard
        bot.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            reply_markup=get_main_menu(user_is_admin)
        )
        # Clear bottom reply keyboard cleanly
        rm_markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "Меню открыто выше ☝️", reply_markup=rm_markup)
    except Exception as e:
        logging.error(f"Error in send_welcome: {e}")
        bot.send_message(chat_id, "Добро пожаловать в Корпус М Мариуполь!", reply_markup=get_main_menu(user_is_admin))


@bot.message_handler(commands=['admin', 'crm', 'analytics', 'dashboard'])
def admin_panel_command(message):
    """Специальная команда админ-панели (только для админов)"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    if not is_admin(user_id=user_id, username=username):
        bot.reply_to(
            message,
            "⛔ <b>Доступ ограничен</b>\n\n"
            "Панель администратора, CRM и аналитика доступны только руководству компании «Корпус М».",
            parse_mode="HTML"
        )
        return

    total_leads = 0
    new_leads = 0
    total_sum = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        total_leads = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0] or 0
        new_leads = c.execute("SELECT COUNT(*) FROM leads WHERE status='Новая'").fetchone()[0] or 0
        total_sum = c.execute("SELECT SUM(estimate) FROM leads").fetchone()[0] or 0
        conn.close()
    except Exception:
        pass

    first_name = html.escape(message.from_user.first_name or "Администратор")

    text = (
        "👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА • КОРПУС М</b>\n\n"
        f"Здравствуйте, <b>{first_name}</b>!\n\n"
        f"📊 <b>Статистика базы:</b>\n"
        f"• Всего заявок: <b>{total_leads}</b>\n"
        f"• Новых в очереди: <b>{new_leads}</b>\n"
        f"• Общая сумма смет: <b>{total_sum:,} ₽</b>\n"
        f"• Канал уведомлений: <b>@saitypodkluch</b>\n\n"
        "Выберите раздел для перехода:"
    ).replace(",", " ")

    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_admin_keyboard())


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    username = call.from_user.username or ""
    user_is_admin = is_admin(user_id=user_id, username=username)

    if chat_id not in user_sessions:
        user_sessions[chat_id] = {}

    data = call.data

    if data == "main_menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "Главное меню мебельного производства <b>«Корпус М» (Мариуполь)</b>:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_main_menu(user_is_admin)
        )

    elif data == "admin_menu":
        bot.answer_callback_query(call.id)
        if not user_is_admin:
            bot.send_message(chat_id, "⛔ Доступ к панели администратора разрешен только руководству.", parse_mode="HTML")
            return
        bot.edit_message_text(
            "👑 <b>Панель Администратора KorpusM:</b>",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )

    elif data == "admin_recent_leads":
        bot.answer_callback_query(call.id)
        if not user_is_admin:
            bot.send_message(chat_id, "⛔ Доступ ограничен.", parse_mode="HTML")
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, created_at, client_name, phone, item_type, estimate, district, status FROM leads ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        conn.close()

        if not rows:
            bot.send_message(chat_id, "📭 В базе пока нет заявок.", parse_mode="HTML")
            return

        text = "📋 <b>Последние заявки из базы:</b>\n\n"
        for r in rows:
            st_icon = "🟡" if r[7] == "Новая" else "⚙️"
            c_name = html.escape(str(r[2]))
            c_phone = html.escape(str(r[3]))
            c_type = html.escape(str(r[4]))
            c_dist = html.escape(str(r[6]))
            text += (
                f"{st_icon} <b>Заказ #KM-{r[0]}</b> ({r[1]})\n"
                f"👤 Клиент: {c_name}\n"
                f"📞 Телефон: <code>{c_phone}</code>\n"
                f"🪑 Изделие: {c_type}\n"
                f"📍 Район: {c_dist}\n"
                f"💰 Оценка: {r[5]:,} ₽\n\n"
            )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📊 Открыть CRM", url=WEBAPP_CRM_URL, web_app=types.WebAppInfo(url=WEBAPP_CRM_URL)),
            types.InlineKeyboardButton("◀ Назад в админку", callback_data="admin_menu")
        )
        bot.send_message(chat_id, text.replace(",", " "), parse_mode="HTML", reply_markup=markup)

    elif data == "admin_stats_summary":
        bot.answer_callback_query(call.id)
        if not user_is_admin:
            bot.send_message(chat_id, "⛔ Доступ ограничен.", parse_mode="HTML")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(estimate), AVG(estimate) FROM leads")
        row = c.fetchone()
        conn.close()

        total_leads = row[0] or 0
        total_sum = row[1] or 0
        avg_sum = int(row[2] or 0)

        text = (
            "💰 <b>Финансовая сводка цеха «Корпус М»</b>\n\n"
            f"• Всего зарегистрировано заявок: <b>{total_leads}</b>\n"
            f"• Суммарный объем смет: <b>{total_sum:,} ₽</b>\n"
            f"• Средний чек проекта: <b>{avg_sum:,} ₽</b>\n"
            "• В производстве: <b>3 активных проекта</b>\n"
        ).replace(",", " ")

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📈 Открыть Аналитику", url=WEBAPP_ANALYTICS_URL, web_app=types.WebAppInfo(url=WEBAPP_ANALYTICS_URL)),
            types.InlineKeyboardButton("◀ Назад в админку", callback_data="admin_menu")
        )
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

    elif data == "show_phone":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            f"📞 <b>Прямой контакт мастера Евгения (Корпус М Мариуполь):</b>\n\n"
            f"<b>{PHONE_NUMBER}</b>\n\n"
            "Звоните в любое удобное время (Пн–Сб с 9:00 до 19:00)!",
            parse_mode="HTML"
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
        text = "🪚 <b>Шаг 1 из 3:</b> Выберите тип мебели для расчета стоимости:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

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
        cur_type = html.escape(user_sessions[chat_id]['item_type'])
        text = f"📏 <b>Шаг 2 из 3:</b> Укажите ориентировочную длину мебели ({cur_type}):"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

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
        text = "🔩 <b>Шаг 3 из 3:</b> Выберите класс фасадов и фурнитуры:"
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

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
            types.InlineKeyboardButton("🌐 Открыть 3D-калькулятор на сайте", url=WEBAPP_SITE_URL, web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
            types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
        )

        res_text = (
            f"🎉 <b>Предварительный расчет готов!</b>\n\n"
            f"🪑 <b>Изделие:</b> {html.escape(item_type)}\n"
            f"📏 <b>Длина:</b> {length_val} м\n"
            f"🔩 <b>Материалы:</b> {html.escape(mat_name)}\n"
            f"💰 <b>Ориентировочная смета:</b> ~ <b>{estimate:,} ₽</b>\n\n"
            "✓ В стоимость включены: 3D-визуализация, распил на ЧПУ, кромление PUR-клеем, доставка и монтаж под ключ в Мариуполе.\n\n"
            "Напишите ваш <b>номер телефона и имя</b> (+7 949 ...), чтобы зафиксировать скидку 10% на материалы и забронировать замер:"
        ).replace(",", " ")

        bot.edit_message_text(res_text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

    elif data == "measure_start":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        for dist in DISTRICTS:
            markup.add(types.InlineKeyboardButton(f"📍 {dist}", callback_data=f"dist_{dist}"))
        markup.add(types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu"))

        text = (
            "📐 <b>Бесплатный выезд мастера на замер по Мариуполю:</b>\n\n"
            "Мастер Евгений приедет с лазерным дальномером и чемоданом образцов (фасады Egger, МДФ, палитра RAL, фурнитура Blum).\n\n"
            "В каком <b>районе Мариуполя</b> находится ваш объект?"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

    elif data.startswith("dist_"):
        bot.answer_callback_query(call.id)
        district = data.replace("dist_", "")
        user_sessions[chat_id]["district"] = district

        text = (
            f"📍 <b>Район выбран:</b> {html.escape(district)}\n\n"
            "Напишите ваш <b>номер телефона и имя</b> (+7 949 ...) для согласования удобного дня и времени замера:"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML")

    elif data == "portfolio_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🌐 Смотреть всё портфолио на сайте", url=WEBAPP_SITE_URL + "#portfolio", web_app=types.WebAppInfo(url=WEBAPP_SITE_URL + "#portfolio")),
            types.InlineKeyboardButton("🪚 Рассчитать стоимость проекта", callback_data="calc_start"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = (
            "📸 <b>Живое портфолио мебельного цеха «Корпус М»:</b>\n\n"
            "• <b>Кухня Графит & Дуб Натуральный</b> (пр. Металлургов) — 210 000 ₽\n"
            "• <b>Кухня Белый мат Soft-Touch & LED</b> (пр. Мира) — 185 000 ₽\n"
            "• <b>Прихожая под потолок с ростовым зеркалом</b> (ул. Нахимова) — 95 000 ₽\n"
            "• <b>Зеркальный шкаф-купе в нишу</b> (бульвар Шевченко) — 75 000 ₽\n"
            "• <b>Торговая мебель и барная стойка STARCOFF</b> — 340 000 ₽\n\n"
            "Все фото в высоком разрешении и видеообзоры доступны на сайте!"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)

    elif data == "reviews_show":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📐 Записаться на замер", callback_data="measure_start"),
            types.InlineKeyboardButton("◀ Назад в меню", callback_data="main_menu")
        )
        text = (
            "⭐ <b>Отзывы наших заказчиков (Мариуполь):</b>\n\n"
            "🗣 <b>Ольга (пр. Мира):</b>\n"
            "«Заказывали кухню под потолок. Сделали за 18 дней, петли Blum работают идеально плавно, ни одного зазора. Спасибо мастеру Евгению!»\n\n"
            "🗣 <b>Артем (Левобережный):</b>\n"
            "«Отличный шкаф-купе и гардеробная. Цены в 1.5 раза приятнее, чем в салонах города, так как работают напрямую из цеха.»\n\n"
            "🗣 <b>Виктория (Приморский):</b>\n"
            "«Идеально спрятали бойлер и трубы в санузле специальным влагостойким шкафом. Очень довольны!»"
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)


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
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB Error: {e}")

    # 2. Duplicate to CRM JSON Store
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
        f"✅ <b>Спасибо, {html.escape(client_name)}! Ваша заявка #{crm_order_id} принята.</b>\n\n"
        f"Мастер Евгений свяжется с вами по номеру <code>{html.escape(text)}</code> в течение 5–10 минут для уточнения деталей и времени замера.\n\n"
        f"📞 Если хотите позвонить прямо сейчас:\n<b>{PHONE_NUMBER}</b>"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🌐 Перейти на сайт Корпус М", url=WEBAPP_SITE_URL, web_app=types.WebAppInfo(url=WEBAPP_SITE_URL)),
        types.InlineKeyboardButton("◀ В главное меню", callback_data="main_menu")
    )

    bot.send_message(chat_id, confirm_text, parse_mode="HTML", reply_markup=markup)


if __name__ == "__main__":
    logging.info("🪵 Korpus M Telegram Bot (@korpus_m_admin_bot) started polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
