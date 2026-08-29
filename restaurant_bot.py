# -*- coding: utf-8 -*-
"""
Telegram Restaurant Bot for «На Бульваре» (Мариуполь)
Bot: @na_bulvare_bot
Token: 8934787717:AAEJU6VPgFAdm9UAmMpQSIyqPDn_k0KUg6c
Сайт: https://nabulvarerest.ru/
CRM: https://nabulvarerest.ru/crm.html
Аналитика: https://nabulvarerest.ru/analytics.html
"""

import os
import sqlite3
import datetime
import logging
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("RESTAURANT_BOT_TOKEN", "8934787717:AAEJU6VPgFAdm9UAmMpQSIyqPDn_k0KUg6c")
ADMIN_USERNAMES = {"den_dev82", "maksim_rest", "illnass777", "denver949", "denver_test", "den_dev", "denver"}
ADMIN_IDS = {"8086868178", "5889459074"}

CRM_URL = "https://nabulvarerest.ru/crm.html"
ANALYTICS_URL = "https://nabulvarerest.ru/analytics.html"
SITE_URL = "https://nabulvarerest.ru/"

bot = telebot.TeleBot(BOT_TOKEN)


def is_admin(user_id=None, username=None):
    if user_id and str(user_id) in ADMIN_IDS:
        return True
    if username:
        u = str(username).strip().lstrip("@").lower()
        if u in ADMIN_USERNAMES:
            return True
    return False


def get_admin_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Вход в CRM-систему", web_app=types.WebAppInfo(url=CRM_URL)),
        types.InlineKeyboardButton("📈 Вход в Аналитику", web_app=types.WebAppInfo(url=ANALYTICS_URL))
    )
    markup.add(
        types.InlineKeyboardButton("🌐 Открыть сайт и Меню", web_app=types.WebAppInfo(url=SITE_URL))
    )
    return markup


def get_admin_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📊 Вход в CRM", web_app=types.WebAppInfo(url=CRM_URL)),
        types.KeyboardButton("📈 Вход в Аналитику", web_app=types.WebAppInfo(url=ANALYTICS_URL))
    )
    markup.add(
        types.KeyboardButton("🎁 Акции на сайте"),
        types.KeyboardButton("🍲 Управление Блюдами")
    )
    markup.add(
        types.KeyboardButton("🔍 Поиск заказа"),
        types.KeyboardButton("📦 Последние заказы")
    )
    markup.add(
        types.KeyboardButton("👥 Управление админами"),
        types.KeyboardButton("📋 Список смены")
    )
    markup.add(
        types.KeyboardButton("🟢 Выйти на смену"),
        types.KeyboardButton("🔴 Завершить смену")
    )
    return markup


def get_guest_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🍽️ Открыть меню и сделать заказ", web_app=types.WebAppInfo(url=SITE_URL))
    )
    return markup


@bot.message_handler(commands=["start", "admin", "panel", "crm", "analytics"])
def handle_start(message):
    uid = message.from_user.id
    uname = message.from_user.username
    full_name = (message.from_user.first_name or "") + " " + (message.from_user.last_name or "")

    if is_admin(uid, uname):
        text = (
            f"👑 <b>ПАНЕЛЬ АДМИНИСТРАТОРА • РЕСТОРАН «НА БУЛЬВАРЕ»</b>\n\n"
            f"Здравствуйте, <b>{full_name.strip() or 'Администратор'}</b>!\n\n"
            f"Вам доступны прямые разделы управления рестораном:\n"
            f"• 📊 <b>CRM-система</b>: Заказы, бронь столиков и гости.\n"
            f"• 📈 <b>Аналитика</b>: Финансовые отчеты и выручка.\n"
            f"• 🎁 <b>Акции & 🍲 Меню</b>: Управление каталогом блюд.\n\n"
            f"<i>Используйте интерактивные кнопки ниже для перехода:</i>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_admin_inline_keyboard())
        bot.send_message(message.chat.id, "Клавиатура управления сменой и цехом активна внизу ⬇️", reply_markup=get_admin_reply_keyboard())
    else:
        text = (
            f"👋 <b>Добро пожаловать в ресторан «На Бульваре»!</b>\n\n"
            f"У нас вы можете заказать вкуснейшие блюда с быстрой доставкой по Мариуполю или забронировать столик.\n\n"
            f"<i>Нажмите кнопку ниже, чтобы открыть онлайн-меню:</i>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_guest_inline_keyboard())


@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    uid = message.from_user.id
    uname = message.from_user.username
    text = (message.text or "").strip()

    if is_admin(uid, uname):
        if "Акции на сайте" in text:
            bot.send_message(message.chat.id, "🎁 <b>Управление Акциями</b>\n\nЧтобы добавить акцию, перейдите в CRM-панель во вкладку Акции или напишите: <code>/add_promo Заголовок | Описание</code>", parse_mode="HTML")
        elif "Управление Блюдами" in text:
            bot.send_message(message.chat.id, "🍲 <b>Управление Блюдами</b>\n\nКаталог блюд доступен для добавления и изменения через CRM.", parse_mode="HTML", reply_markup=get_admin_inline_keyboard())
        elif "Поиск заказа" in text:
            bot.send_message(message.chat.id, "🔍 Введите номер заказа (например: <code>NB-1024</code>) или телефон гостя:", parse_mode="HTML")
        elif "Последние заказы" in text:
            bot.send_message(message.chat.id, "📦 Откройте CRM-панель для просмотра полного списка заказов в реальном времени.", parse_mode="HTML", reply_markup=get_admin_inline_keyboard())
        elif "Выйти на смену" in text:
            bot.send_message(message.chat.id, "🟢 <b>Вы вышли на смену!</b> Уведомления о новых заказах и бронях столиков будут приходить вам.", parse_mode="HTML")
        elif "Завершить смену" in text:
            bot.send_message(message.chat.id, "🔴 <b>Смена завершена.</b> Хорошего отдыха!", parse_mode="HTML")
        elif "Список смены" in text:
            bot.send_message(message.chat.id, "📋 <b>Администраторы на смене:</b>\n1. Den | (@den_dev82)\n2. Максим (@maksim_rest)", parse_mode="HTML")
        elif "Управление админами" in text:
            bot.send_message(message.chat.id, "👥 <b>Список администраторов ресторана:</b>\n• @den_dev82 (ID 5889459074)\n• @maksim_rest\n• @illnass777\n• 8086868178", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "👑 Выберите раздел в меню:", reply_markup=get_admin_inline_keyboard())
    else:
        bot.send_message(message.chat.id, "🍽️ Откройте меню ресторана «На Бульваре»:", reply_markup=get_guest_inline_keyboard())


if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except Exception:
        pass
    logging.info("🍲 Restaurant «На Бульваре» Bot (@na_bulvare_bot) started polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
