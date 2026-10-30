# -*- coding: utf-8 -*-
import asyncio
import json
import sqlite3
import urllib.parse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import Command

# --- CONFIG ---
BOT_TOKEN = "9283181292:AAHkFmHCxh-bvfC7zlCwcsrCvapOyzfJ-GA"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WEBAPP_BASE_URL = "https://github.io"

# --- DATABASE MECHANICAL ---
def init_db():
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 1000)')
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, item_value INTEGER)')
    conn.commit()
    conn.close()

def get_balance(uid):
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id = ?', (uid,))
    res = c.fetchone()
    if not res:
        c.execute('INSERT INTO users (user_id) VALUES (?)', (uid,))
        conn.commit()
        conn.close()
        return 1000
    conn.close()
    return res

def set_balance(uid, amount):
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, uid))
    conn.commit()
    conn.close()

def add_to_inventory(uid, name, value):
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('INSERT INTO inventory (user_id, item_name, item_value) VALUES (?, ?, ?)', (uid, str(name), value))
    conn.commit()
    conn.close()

def get_inventory_json(uid):
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('SELECT id, item_name, item_value FROM inventory WHERE user_id = ?', (uid,))
    rows = c.fetchall()
    conn.close()
    
    # 🌟 ІДЕАЛЬНЕ ВИПРАВЛЕННЯ: беремо цілу назву предмета r[1], а не літери окремо!
    inv_list = [{"id": r[0], "name": str(r[1]), "value": r[2]} for r in rows]
    return urllib.parse.quote(json.dumps(inv_list))

def delete_item(item_id):
    conn = sqlite3.connect('brainrot_loot.db')
    c = conn.cursor()
    c.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

# --- GENERATE REFRESH BUTTON ---
def get_main_menu(uid):
    init_db()
    bal = get_balance(uid)
    inv = get_inventory_json(uid)
    full_url = f"{WEBAPP_BASE_URL}?balance={bal}&inventory={inv}"
    kb = [[KeyboardButton(text="🎮 ГРАТИ (Brainrot Loot)", web_app=WebAppInfo(url=full_url))]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    await message.answer(
        f"💥 **Баланс та Інвентар успішно синхронізовано!** 💥\n\n"
        f"Натискай велику кнопку **ГРАТИ** нижче, щоб відкрити графічний екран гри! 👇",
        reply_markup=get_main_menu(uid)
    )

# --- ПРИЙОМ ДАНИХ З ГРАФІЧНОГО ЕКРАНУ ---
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    uid = message.from_user.id
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get("action") == "open_case":
            new_bal = data.get("new_balance")
            item_n = data.get("item")
            item_v = data.get("val")
            set_balance(uid, new_bal)
            add_to_inventory(uid, item_n, item_v)
            await message.answer(f"🎰 **Кейс відкрито!**\nВипав предмет: *{item_n}*\nБаланс оновлено!", reply_markup=get_main_menu(uid), parse_mode="Markdown")
            
        elif data.get("action") == "sell_item":
            item_id = data.get("item_id")
            new_bal = data.get("new_balance")
            delete_item(item_id)
            set_balance(uid, new_bal)
            await message.answer(f"💰 **Предмет успішно продано!** Монети зараховано на баланс сервера.", reply_markup=get_main_menu(uid))
            
        elif data.get("action") == "upgrade":
            new_bal = data.get("res_balance")
            set_balance(uid, new_bal)
            if data.get("success"):
                add_to_inventory(uid, data.get("target_item"), data.get("target_val"))
                await message.answer("🔮 **Апгрейд успішний!** Твій новий предмет додано в базу.", reply_markup=get_main_menu(uid))
            else:
                await message.answer("💥 **Апгрейд невдалий!** Старий предмет видалено з бази.", reply_markup=get_main_menu(uid))
                
    except Exception as e:
        print(f"Помилка синхронізації: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
