import asyncio
import logging
import sqlite3
import time
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand

# ==================== CONFIGURATION ====================
TOKEN = "8855603359:AAG5KiEcEZOVbrkCYuPOB9wusoZLL22Mlog"
ADMIN_ID = 1332736076  
SUPPORT_USERNAME = "GUODA36"

VODAFONE_NUMBER = "01008924340"
USDT_TRC20_ADDRESS = "TZFH6r1gLj94GWMqAQ71p3uixB7HTd9ZVL"

USDT_EGP_RATE = 50.0  
MIN_DEPOSIT_AMOUNT = 200.0  
SELLER_UPGRADE_COST_EGP = 1250.0 
SELLER_MIN_WITHDRAW = 200.0 

DEFAULT_PLATFORM_FEE = 0.02  

LOG_CHANNEL_ID = -1004393845755      
DELIVERY_PROOF_CHANNEL_ID = -1004490105003
GUIDE_UPDATES_CHANNEL_ID = -1003836643803
STOCK_ALERT_CHANNEL_ID = -1004486768828

GUIDE_UPDATES_LINK = "https://t.me/+r3C8qot_U7ExZTU0"
DELIVERY_PROOF_LINK = "https://t.me/c/4490105003/1"
STOCK_ALERT_LINK = "https://t.me/c/4486768828/1"

PRODUCTS_PRICES_EGP = {
    "ff110": 42.0, "ff231": 84.0, "ff583": 210.0, "ff1188": 420.0, "ff2420": 850.0,
    "pubg60": 42.0, "pubg325": 210.0, "pubg660": 420.0, "pubg1800": 1100.0, "pubg3850": 2200.0, "pubg8100": 4500.0
}

PRODUCTS_PRICES_USDT = {
    "ff110": 0.84, "ff231": 1.68, "ff583": 4.20, "ff1188": 8.40, "ff2420": 17.0,
    "pubg60": 0.84, "pubg325": 4.20, "pubg660": 8.40, "pubg1800": 22.0, "pubg3850": 44.0, "pubg8100": 90.0
}

PRODUCTS_TITLES = {
    "ff110": "Free Fire 110 💎", "ff231": "Free Fire 231 💎", "ff583": "Free Fire 583 💎", "ff1188": "Free Fire 1188 💎", "ff2420": "Free Fire 2420 💎",
    "pubg60": "PUBG Mobile 60 🪙", "pubg325": "PUBG Mobile 325 🪙", "pubg660": "PUBG Mobile 660 🪙", "pubg1800": "PUBG Mobile 1800 🪙", "pubg3850": "PUBG Mobile 3850 🪙", "pubg8100": "PUBG Mobile 8100 🪙"
}

ALL_PRODUCT_KEYS = [
    "ff110", "ff231", "ff583", "ff1188", "ff2420",
    "pubg60", "pubg325", "pubg660", "pubg1800", "pubg3850", "pubg8100"
]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

DB_NAME = "store_v25_escrow.db"
user_last_action = {}
SPAM_DELAY = 0.5  
maintenance_mode = False  

def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0,
            has_purchased INTEGER DEFAULT 0,
            is_seller INTEGER DEFAULT 0,
            seller_balance REAL DEFAULT 0.0,
            seller_pending_balance REAL DEFAULT 0.0,
            seller_sales_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            last_wheel_spin TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_title TEXT,
            product_key TEXT,
            user_username TEXT,
            seller_id INTEGER DEFAULT 0,
            item_price REAL DEFAULT 0.0,
            payment_type TEXT DEFAULT 'wallet',
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_deposits (
            deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            details TEXT,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_key TEXT,
            code TEXT UNIQUE,
            seller_id INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            game_code TEXT,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchased_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            seller_id INTEGER,
            product_name TEXT,
            game_code TEXT,
            price REAL,
            net_profit REAL DEFAULT 0.0,
            purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_refunded INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            confirmed_delivery INTEGER DEFAULT 0,
            escrow_released INTEGER DEFAULT 0,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seller_withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            amount REAL,
            details TEXT,
            status TEXT DEFAULT 'pending',
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_key TEXT,
            UNIQUE(user_id, product_key)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_prices (
            product_key TEXT PRIMARY KEY,
            price_egp REAL,
            price_usdt REAL
        )
    """)
    
    for p_key in PRODUCTS_PRICES_EGP.keys():
        egp_val = PRODUCTS_PRICES_EGP[p_key]
        usdt_val = PRODUCTS_PRICES_USDT[p_key]
        cursor.execute("INSERT OR IGNORE INTO product_prices (product_key, price_egp, price_usdt) VALUES (?, ?, ?)", (p_key, egp_val, usdt_val))

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN seller_pending_balance REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_wheel_spin TIMESTAMP")
        cursor.execute("ALTER TABLE purchased_transactions ADD COLUMN net_profit REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE purchased_transactions ADD COLUMN escrow_released INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

def get_product_prices(product_key):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT price_egp, price_usdt FROM product_prices WHERE product_key = ?", (product_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except:
        pass
    return PRODUCTS_PRICES_EGP.get(product_key, 0.0), PRODUCTS_PRICES_USDT.get(product_key, 0.0)

def get_stock_count(product_key):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock WHERE product_key = ? AND status = 'active'", (product_key,))
        cnt = cursor.fetchone()[0]
        conn.close()
        return cnt
    except:
        return 0

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Main Menu"),
        BotCommand(command="seller", description="Seller Panel"),
        BotCommand(command="profile", description="My Profile"),
        BotCommand(command="deposit", description="Deposit Balance"),
        BotCommand(command="help", description="Support & FAQ"),
        BotCommand(command="support", description="Customer Support"),
    ]
    await bot.set_my_commands(commands)

@router.message.outer_middleware()
@router.callback_query.outer_middleware()
async def anti_spam_middleware(handler, event, data):
    user = event.from_user if hasattr(event, "from_user") else None
    if user and user.id != ADMIN_ID:
        if maintenance_mode:
            if isinstance(event, types.CallbackQuery):
                await event.answer("⚠️ Bot is currently under maintenance. Please try again later.", show_alert=True)
            elif isinstance(event, types.Message):
                await event.answer("⚠️ Bot is currently under maintenance. Please try again later.")
            return

        try:
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM users WHERE user_id = ?", (user.id,))
            res = cursor.fetchone()
            conn.close()
            if res and res[0] == 'blocked':
                if isinstance(event, types.CallbackQuery):
                    await event.answer("You are blocked from using this bot.", show_alert=True)
                elif isinstance(event, types.Message):
                    await event.answer("🚫 You are blocked from using this bot.")
                return
        except:
            pass

        current_time = time.time()
        last_time = user_last_action.get(user.id, 0)
        if current_time - last_time < SPAM_DELAY:
            if isinstance(event, types.CallbackQuery):
                try:
                    await event.answer("Please wait a moment before sending again.", show_alert=True)
                except:
                    pass
            return
        user_last_action[user.id] = current_time

    return await handler(event, data)

async def safe_answer_callback(callback: types.CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest:
        pass

def get_user_balance(user_id):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res and res[0] is not None else 0.0
    except:
        return 0.0

def get_seller_data(user_id):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT seller_balance, seller_pending_balance, seller_sales_count, is_seller, full_name, username FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res if res else (0.0, 0.0, 0, 0, "Unknown", "N/A")
    except:
        return (0.0, 0.0, 0, 0, "Unknown", "N/A")

def is_user_seller(user_id):
    if user_id == ADMIN_ID: return True
    _, _, _, is_sell, _, _ = get_seller_data(user_id)
    return is_sell == 1

def save_user(user_id, full_name, username):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, status FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(
            "INSERT INTO users (user_id, full_name, username, balance, has_purchased, is_seller, seller_balance, seller_pending_balance, seller_sales_count, status) VALUES (?, ?, ?, 0.0, 0, 0, 0.0, 0.0, 0, 'active')",
            (user_id, full_name, username)
        )
    else:
        if exists[1] != 'blocked':
            cursor.execute("UPDATE users SET full_name = ?, username = ?, status = 'active' WHERE user_id = ?", (full_name, username, user_id))
        
    conn.commit()
    conn.close()

def save_active_order(user_id, product_title, product_key, user_username, seller_id=0, item_price=0.0, payment_type="wallet", receipt_file_id=None):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO active_orders (user_id, product_title, product_key, user_username, seller_id, item_price, payment_type, receipt_file_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, product_title, product_key, user_username, seller_id, item_price, payment_type, receipt_file_id)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_active_order(order_id):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, product_title, product_key, user_username, seller_id, item_price, payment_type, receipt_file_id FROM active_orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_pending_orders():
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, user_id, product_title, user_username, payment_type FROM active_orders WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_active_order(order_id):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_orders WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

def save_user_purchased_code(user_id, product_name, game_code, seller_id=0, price=0.0, net_profit=0.0):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO user_codes (user_id, product_name, game_code, date_time) VALUES (?, ?, ?, ?)", (user_id, product_name, game_code, current_time))
    cursor.execute("INSERT INTO purchased_transactions (user_id, seller_id, product_name, game_code, price, net_profit, purchase_time, date_time, escrow_released) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)", 
                   (user_id, seller_id, product_name, game_code, price, net_profit, current_time, current_time))
    trans_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trans_id

def get_stock_code(product_key):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, seller_id, price FROM stock WHERE product_key = ? AND status = 'active' LIMIT 1", (product_key,))
    row = cursor.fetchone()
    if row:
        stock_id, code, seller_id, price = row
        cursor.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM stock WHERE product_key = ? AND status = 'active'", (product_key,))
        rem_count = cursor.fetchone()[0]
        conn.close()
        
        if rem_count <= 3:
            asyncio.create_task(notify_low_stock(product_key, rem_count))
            
        return code, seller_id, price
    conn.close()
    return None, 0, 0.0

async def notify_low_stock(product_key, rem_count):
    p_name = PRODUCTS_TITLES.get(product_key, product_key)
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ <b>Low Stock Warning!</b>\n\nProduct: <b>{p_name}</b>\nRemaining items in inventory: <b>{rem_count} codes left</b>."
        )
    except:
        pass

async def notify_subscribed_users_new_stock(product_key, count=1):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM stock_subscriptions WHERE product_key = ?", (product_key,))
    subs = cursor.fetchall()
    if subs:
        cursor.execute("DELETE FROM stock_subscriptions WHERE product_key = ?", (product_key,))
        conn.commit()
    conn.close()

    p_title = PRODUCTS_TITLES.get(product_key, product_key)
    
    try:
        await bot.send_message(
            chat_id=STOCK_ALERT_CHANNEL_ID,
            text=f"📦 <b>New Stock Added!</b>\n\nProduct: <b>{p_title}</b>\nQuantity Added: <b>{count} Code(s)</b> 💎"
        )
    except Exception as e:
        logging.error(f"Failed to send stock alert channel msg: {e}")

    for (u_id,) in subs:
        try:
            builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="⚡ Buy Now", callback_data=f"buy_{product_key}"))
            await bot.send_message(
                chat_id=u_id,
                text=f"🔔 <b>Back in Stock Notification!</b>\n\nProduct <b>{p_title}</b> is now available again in store!",
                reply_markup=builder.as_markup()
            )
        except:
            pass

class OrderState(StatesGroup):
    waiting_for_wallet_number = State()
    waiting_for_external_receipt = State()
    waiting_for_external_details = State()

class DepositState(StatesGroup):
    waiting_for_deposit_amount = State()
    waiting_for_deposit_receipt = State()

class SellerWithdrawState(StatesGroup):
    waiting_for_seller_withdraw = State()

class SellerState(StatesGroup):
    waiting_for_seller_stock = State()

class AdminState(StatesGroup):
    waiting_for_code = State()
    waiting_for_reject_reason = State()
    waiting_for_broadcast = State()
    waiting_for_stock = State()
    waiting_for_deposit_reject = State()
    waiting_for_refund_reject_reason = State()
    waiting_for_balance_change = State()
    waiting_for_warning = State()
    waiting_for_seller_toggle = State()
    waiting_for_new_price_egp = State()
    waiting_for_new_price_usdt = State()
    waiting_for_seller_balance_adjust = State()
    waiting_for_ban_user_id = State()
    
    waiting_for_full_price_input = State()
    waiting_for_full_price_hours = State()

class QuickSearchState(StatesGroup):
    waiting_for_player_id = State()

class AdminSetPriceState(StatesGroup):
    waiting_for_price = State()

class IDTicketState(StatesGroup):
    waiting_for_player_id = State()
    waiting_for_quantity = State()

@router.callback_query(F.data == "start_id_ticket")
async def start_id_ticket_process(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(IDTicketState.waiting_for_player_id)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data="main_menu"))
    await callback.message.edit_text(
        "🎫 <b>فتح تيكيت شحن ID المباشر:</b>\n\nأرسل الـ Player ID (الأيدي) الخاص بك الآن:",
        reply_markup=builder.as_markup()
    )
    await safe_answer_callback(callback)

@router.message(IDTicketState.waiting_for_player_id)
async def process_ticket_player_id(message: types.Message, state: FSMContext):
    player_id = message.text.strip()
    await state.update_data(ticket_player_id=player_id)
    await state.set_state(IDTicketState.waiting_for_quantity)
    await message.answer(f"✅ تم تسجيل الـ ID: <code>{player_id}</code>\n\nالآن أرسل الكمية / الباقة المطلوبة:")

@router.message(IDTicketState.waiting_for_quantity)
async def process_ticket_quantity(message: types.Message, state: FSMContext):
    quantity = message.text.strip()
    data = await state.get_data()
    player_id = data.get("ticket_player_id")
    user = message.from_user
    username_str = f"@{user.username}" if user.username else "لا يوجد"

    admin_notice = (
        f"🎫 <b>تيكيت شحن ID جديد!</b>\n\n"
        f"👤 <b>العميل:</b> {user.full_name} ({username_str})\n"
        f"🆔 <b>آي دي العميل:</b> <code>{user.id}</code>\n"
        f"🎮 <b>Player ID للشحن:</b> <code>{player_id}</code>\n"
        f"📦 <b>الكمية المطلوبة:</b> <b>{quantity}</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💰 حدد السعر ووسيلة الدفع للعميل", callback_data=f"set_price_t_{user.id}"))
    builder.row(types.InlineKeyboardButton(text="✅ تم الشحن وإغلاق التيكيت", callback_data=f"close_ticket_{user.id}"))

    await bot.send_message(chat_id=ADMIN_ID, text=admin_notice, reply_markup=builder.as_markup())
    await message.answer("✅ <b>تم فتح التيكيت وإرساله للآدمن بنجاح!</b>\nسيصلك إشعار بالسعر وطريقة الدفع فوراً.")
    await state.clear()

@router.callback_query(F.data.startswith("set_price_t_"))
async def admin_start_set_ticket_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    target_user_id = int(callback.data.split("_")[3])
    await state.update_data(target_ticket_user=target_user_id)
    await state.set_state(AdminSetPriceState.waiting_for_price)
    await callback.message.reply("✍️ **أدخل السعر المطلوب من العميل بالجنيه (EGP):**")
    await safe_answer_callback(callback)

@router.message(AdminSetPriceState.waiting_for_price)
async def admin_send_ticket_price_options(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        price = float(message.text.strip())
        data = await state.get_data()
        target_user_id = data.get("target_ticket_user")
        usdt_price = price / USDT_EGP_RATE

        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="🇪🇬 فودافون كاش", callback_data=f"send_pay_voda_{target_user_id}_{price}"),
            types.InlineKeyboardButton(text="🌐 عملة USDT (TRC20)", callback_data=f"send_pay_usdt_{target_user_id}_{usdt_price}")
        )

        await message.answer(
            f"💰 السعر المكتوب: <b>{price:.2f} EGP</b> (~${usdt_price:.2f} USDT)\nاختر طريقة الدفع التي ستبعتها للعميل:",
            reply_markup=builder.as_markup()
        )
    except ValueError:
        await message.answer("❌ يرجى كتابة السعر بالأرقام فقط:")

@router.callback_query(F.data.startswith("send_pay_"))
async def send_payment_details_to_user(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    p_type = parts[2]
    target_user_id = int(parts[3])
    amount = float(parts[4])

    if p_type == "voda":
        pay_msg = (
            f"💳 <b>تسعيرة طلب الشحن الخاص بك:</b>\n\n"
            f"💰 المبلغ المطلوب: <b>{amount:.2f} EGP</b>\n"
            f"📱 رقم فودافون كاش للتحويل: <code>{VODAFONE_NUMBER}</code>\n\n"
            f"📸 بعد التحويل، قم بإرسال صورة الإيصال هنا لتأكيد الطلب."
        )
    else:
        pay_msg = (
            f"💳 <b>تسعيرة طلب الشحن الخاص بك:</b>\n\n"
            f"💰 المبلغ المطلوب: <b>${amount:.2f} USDT</b>\n"
            f"🌐 عنوان المحفظة TRC20: <code>{USDT_TRC20_ADDRESS}</code>\n\n"
            f"📸 بعد التحويل، قم بإرسال صورة الإيصال هنا لتأكيد الطلب."
        )

    try:
        await bot.send_message(chat_id=target_user_id, text=pay_msg)
        await callback.message.edit_text(callback.message.text + "\n\n✅ تم إرسال بيانات الدفع والسعر للعميل بنجاح.")
    except Exception as e:
        await callback.message.reply(f"❌ تعذر الإرسال للعميل: {e}")
    await safe_answer_callback(callback)

def get_last_purchased_product(user_id):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT product_name FROM purchased_transactions WHERE user_id = ? AND is_refunded = 0 ORDER BY id DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            p_name = row[0]
            for key, title in PRODUCTS_TITLES.items():
                if title == p_name:
                    return key, title
        return None, None
    except:
        return None, None

def get_main_keyboard(user_id):
    builder = InlineKeyboardBuilder()
    
    last_key, last_title = get_last_purchased_product(user_id)
    if last_key:
        builder.row(types.InlineKeyboardButton(text=f"⚡ Repeat Last Order ({last_title})", callback_data=f"buy_{last_key}"))

    builder.row(types.InlineKeyboardButton(text="🔥 Free Fire", callback_data="cat_freefire"))
    builder.row(types.InlineKeyboardButton(text="🎮 PUBG Mobile", callback_data="cat_pubg"))
    builder.row(types.InlineKeyboardButton(text="🎫 تيكيت شحن ID direct", callback_data="start_id_ticket"))
    builder.row(types.InlineKeyboardButton(text="🎡 عجلة الحظ (هدية يومية)", callback_data="spin_wheel_daily"))
    builder.row(types.InlineKeyboardButton(text="🔍 Quick Search by Player ID", callback_data="quick_search_id"))
    
    builder.row(
        types.InlineKeyboardButton(text="📖 Guides & Updates", url=GUIDE_UPDATES_LINK),
        types.InlineKeyboardButton(text="📦 Live Stock Channel", url=STOCK_ALERT_LINK)
    )
    # تم إزالة زر Live Deliveries Channel من هنا بناءً على طلبك
    
    builder.row(
        types.InlineKeyboardButton(text="👤 My Profile", callback_data="my_profile"),
        types.InlineKeyboardButton(text="📦 Purchase History", callback_data="my_codes_history")
    )
    builder.row(types.InlineKeyboardButton(text="💳 Deposit Balance", callback_data="deposit_balance"))
    builder.row(types.InlineKeyboardButton(text="❓ FAQ & Support", callback_data="faq_menu"))
    
    if is_user_seller(user_id):
        builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    else:
        builder.row(types.InlineKeyboardButton(text="⭐ Upgrade to Seller", callback_data="upgrade_to_seller"))

    if user_id == ADMIN_ID:
        builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        
    builder.row(types.InlineKeyboardButton(text="ℹ️ About Store", callback_data="about_store"))
    return builder.as_markup()

# ==================== WHEEL OF FORTUNE (DAILY BONUS) ====================

@router.callback_query(F.data == "spin_wheel_daily")
async def spin_wheel_daily_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT last_wheel_spin FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    now = datetime.now()
    if row and row[0]:
        last_spin = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if now - last_spin < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_spin)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await safe_answer_callback(
                callback, 
                f"⏳ لقد حصلت على هديتك اليومية بالفعل!\nعد مجدداً بعد {hours} ساعة و {minutes} دقيقة.", 
                show_alert=True
            )
            conn.close()
            return

    prizes = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 200.0]
    weights = [45.0, 30.0, 15.0, 6.0, 3.0, 0.5, 0.5] 
    
    won_amount = random.choices(prizes, weights=weights, k=1)[0]
    
    cursor.execute(
        "UPDATE users SET balance = balance + ?, last_wheel_spin = ? WHERE user_id = ?", 
        (won_amount, now.strftime("%Y-%m-%d %H:%M:%S"), user_id)
    )
    conn.commit()
    conn.close()
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    
    if won_amount == 200.0:
        prize_msg = f"🎉 🎉 <b>مستحيل!! لقد فزت بالجائزة الكبرى: {won_amount:.0f} جنيه!</b> 🎁\nتم إضافتها لحسابك الآن!"
    else:
        prize_msg = f"🎡 <b>مبروك! لفيت عجلة الحظ وفزت بمكافأة: {won_amount} جنيه 🎁</b>\nتم إضافة المبلغ تلقائياً إلى رصيد محفظتك!"
        
    try:
        await callback.message.edit_text(prize_msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket_by_admin(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    target_user_id = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="✅ <b>تم شحن طلبك بنجاح عن طريق الـ ID وإغلاق التيكيت! نتمنى لك تجربة ممتعة 🎮</b>"
        )
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>تم إغلاق التيكيت وتأكيد الشحن للعميل.</b>")
    except:
        pass
    await safe_answer_callback(callback, "تم الإغلاق بنجاح.")

# ==================== SELECTION MENU WITH LIVE STOCK ====================

@router.callback_query(F.data.in_(["cat_freefire", "cat_pubg"]))
async def ask_currency_selection(callback: types.CallbackQuery):
    cat_type = callback.data.replace("cat_", "")
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🇪🇬 EGP (Egyptian Pound)", callback_data=f"cur_egp_{cat_type}"))
    builder.row(types.InlineKeyboardButton(text="🌐 USDT (US Dollar)", callback_data=f"cur_usdt_{cat_type}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    
    try:
        await callback.message.edit_text(
            "💱 <b>Choose Display Currency:</b>\nPlease select your preferred currency to view prices:", 
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("cur_"))
async def show_category_products_filtered(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    curr = parts[1]      
    cat_type = parts[2]  
    
    builder = InlineKeyboardBuilder()
    
    if cat_type == "freefire":
        items = ["ff110", "ff231", "ff583", "ff1188", "ff2420"]
        header_title = "🔥 Free Fire ID (Available)"
    else:
        items = ["pubg60", "pubg325", "pubg660", "pubg1800", "pubg3850", "pubg8100"]
        header_title = "🎮 PUBG Mobile ID (Available)"

    for p_key in items:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        egp_p, usdt_p = get_product_prices(p_key)
        stock_qty = get_stock_count(p_key)
        
        stock_str = f"({stock_qty})" if stock_qty > 0 else "(نفذت ❌)"
        
        if curr == "egp":
            btn_text = f"{title} - {egp_p:.0f} EGP {stock_str}"
        else:
            btn_text = f"{title} - ${usdt_p:.2f} USDT {stock_str}"
            
        builder.row(types.InlineKeyboardButton(text=btn_text, callback_data=f"buy_{p_key}_{curr}"))

    builder.row(types.InlineKeyboardButton(text="⬅️ تغيير العملة", callback_data=f"cat_{cat_type}"))
    builder.row(types.InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu"))
    
    try:
        await callback.message.edit_text(
            f"📦 <b>{header_title}:</b>\nاختر الباقة المناسبة للشحن الفوري:", 
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

# ==================== OTHER KEYBOARDS & PANELS ====================

def get_seller_keyboard(user_id):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock WHERE seller_id = ? AND status = 'active'", (user_id,))
    active_stock_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(price) FROM purchased_transactions WHERE seller_id = ? AND is_refunded = 0", (user_id,))
    sales_row = cursor.fetchone()
    conn.close()
    
    total_sales_cnt = sales_row[0] if sales_row and sales_row[0] else 0

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=f"📊 Quick Stats: {total_sales_cnt} Sales | {active_stock_count} Stock Active", callback_data="seller_panel_btn"))
    builder.row(types.InlineKeyboardButton(text="➕ Add Stock Code", callback_data="seller_add_stock"))
    builder.row(types.InlineKeyboardButton(text="📋 My Stock", callback_data="seller_view_my_stock"))
    builder.row(types.InlineKeyboardButton(text="📊 My Sales History", callback_data="seller_sales_history"))
    builder.row(types.InlineKeyboardButton(text="📜 Financial Ledger", callback_data="seller_financial_ledger"))
    builder.row(types.InlineKeyboardButton(text="💰 Withdraw Profits", callback_data="seller_balance_menu"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()

def get_admin_keyboard():
    global maintenance_mode
    maint_text = "🟢 Disable Maintenance" if maintenance_mode else "🔴 Enable Maintenance"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📦 Add Stock", callback_data="adm_addstock"))
    builder.row(types.InlineKeyboardButton(text="📊 Stock Quick Overview", callback_data="adm_stock_overview"))
    builder.row(types.InlineKeyboardButton(text="📋 View All Active Stock Codes", callback_data="adm_view_all_codes"))
    builder.row(types.InlineKeyboardButton(text="✏️ Edit Product Prices (EGP / USDT)", callback_data="adm_edit_prices_menu"))
    builder.row(types.InlineKeyboardButton(text="🚀 جدولة تعديل الأسعار شامل + إذاعة", callback_data="adm_full_price_schedule_start"))
    builder.row(types.InlineKeyboardButton(text="📈 Comprehensive Sales Analytics", callback_data="adm_sales_analytics"))
    builder.row(types.InlineKeyboardButton(text="💎 Net Profit Report", callback_data="adm_net_profits"))
    builder.row(types.InlineKeyboardButton(text="👥 Users Balances", callback_data="adm_users_balances"))
    builder.row(types.InlineKeyboardButton(text="⭐ Sellers List & Control", callback_data="adm_sellers_list"))
    builder.row(types.InlineKeyboardButton(text="🔑 Sellers Stock & Sales", callback_data="adm_sellers_stock_list"))
    builder.row(types.InlineKeyboardButton(text="⏳ Pending Orders", callback_data="adm_pending_orders"))
    builder.row(types.InlineKeyboardButton(text="💸 Pending Withdrawals", callback_data="adm_pending_withdrawals"))
    builder.row(types.InlineKeyboardButton(text="⚙️ Add/Deduct Balance", callback_data="adm_manage_balance"))
    builder.row(types.InlineKeyboardButton(text="🔨 Ban / Unban Users Menu", callback_data="adm_ban_menu"))
    builder.row(types.InlineKeyboardButton(text="📜 Admin Ledger History", callback_data="adm_ledger_history"))
    builder.row(types.InlineKeyboardButton(text="⚠️ Send Warning", callback_data="adm_warning_menu"))
    builder.row(types.InlineKeyboardButton(text="📊 Bot Users Report", callback_data="adm_users_report"))
    builder.row(types.InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"))
    builder.row(types.InlineKeyboardButton(text=maint_text, callback_data="adm_toggle_maintenance"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()

# ==================== SYSTEM FOR BULK FULL PRICE UPDATE & SCHEDULED BROADCAST ====================

@router.callback_query(F.data == "adm_full_price_schedule_start")
async def start_full_price_schedule(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    
    await state.update_data(new_prices_map={}, current_step_index=0)
    await state.set_state(AdminState.waiting_for_full_price_input)
    
    first_p_key = ALL_PRODUCT_KEYS[0]
    first_p_title = PRODUCTS_TITLES.get(first_p_key, first_p_key)
    curr_egp, _ = get_product_prices(first_p_key)
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_btn"))
    
    await callback.message.edit_text(
        f"🚀 <b>بدء جدولة تعديل أسعار المنتجات كاملة:</b>\n\n"
        f"سنقوم بإدخال السعر الجديد لكل باقة خطوة بخطوة.\n"
        f"1️⃣ المنتجات 1/{len(ALL_PRODUCT_KEYS)}: <b>{first_p_title}</b>\n"
        f"السعر الحالي: <b>{curr_egp} EGP</b>\n\n"
        f"✍️ أرسل **السعر الجديد بالجنيه المصري (EGP)** الآن:",
        reply_markup=builder.as_markup()
    )
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_full_price_input)
async def process_full_price_input(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        new_price = float(message.text.strip())
        if new_price <= 0:
            await message.reply("❌ يرجى إدخال سعر صحيح أكبر من الصفر:")
            return
            
        data = await state.get_data()
        new_prices_map = data.get("new_prices_map", {})
        idx = data.get("current_step_index", 0)
        
        current_p_key = ALL_PRODUCT_KEYS[idx]
        new_prices_map[current_p_key] = new_price
        
        next_idx = idx + 1
        if next_idx < len(ALL_PRODUCT_KEYS):
            await state.update_data(new_prices_map=new_prices_map, current_step_index=next_idx)
            next_p_key = ALL_PRODUCT_KEYS[next_idx]
            next_p_title = PRODUCTS_TITLES.get(next_p_key, next_p_key)
            curr_egp, _ = get_product_prices(next_p_key)
            
            await message.answer(
                f"✅ تم حفظ السعر للباقة السابقة!\n\n"
                f"المنتج {next_idx+1}/{len(ALL_PRODUCT_KEYS)}: <b>{next_p_title}</b>\n"
                f"السعر الحالي: <b>{curr_egp} EGP</b>\n\n"
                f"✍️ أرسل **السعر الجديد بالجنيه (EGP)**:"
            )
        else:
            await state.update_data(new_prices_map=new_prices_map)
            await state.set_state(AdminState.waiting_for_full_price_hours)
            
            await message.answer(
                f"🎉 <b>تم إدخال أسعار جميع الباقات بنجاح!</b>\n\n"
                f"⏱️ أرسل الآن **عدد الساعات** التي تريد تطبيق التعديل بعدها أوتوماتيكياً (مثلاً أرسل `3` أو `5`):"
            )
            
    except ValueError:
        await message.reply("❌ صيغة غير صحيحة. أرسل الأرقام فقط (مثال: `45` أو `90`):")

@router.message(AdminState.waiting_for_full_price_hours)
async def process_full_price_hours(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        hours_val = float(message.text.strip())
        if hours_val <= 0:
            await message.reply("❌ يجب أن يكون الوقت أكبر من 0:")
            return
            
        data = await state.get_data()
        new_prices_map = data.get("new_prices_map", {})
        
        await state.update_data(scheduled_hours=hours_val)
        
        summary_text = f"📋 <b>ملخص التعديل الجديد للأسعار (سيتم تطبيقه بعد {hours_val} ساعات):</b>\n\n"
        for p_key, new_p in new_prices_map.items():
            p_title = PRODUCTS_TITLES.get(p_key, p_key)
            old_p, _ = get_product_prices(p_key)
            summary_text += f"• {p_title}: <s>{old_p:.0f} EGP</s> ➔ <b>{new_p:.0f} EGP</b>\n"
            
        summary_text += "\nهل تريد الموافقة وإرسال الإذاعة التنبيهية لجميع الأعضاء الآن؟"
        
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="✅ موافقة وإرسال الإذاعة فوراً", callback_data="confirm_full_sched_exec"))
        builder.row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_btn"))
        
        await message.answer(summary_text, reply_markup=builder.as_markup())
        
    except ValueError:
        await message.reply("❌ أرسل رقم الساعات بشكل صحيح (مثال: `3`):")

@router.callback_query(F.data == "confirm_full_sched_exec")
async def confirm_and_broadcast_full_schedule(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    new_prices_map = data.get("new_prices_map")
    hours_val = data.get("scheduled_hours", 1.0)
    
    if not new_prices_map:
        await safe_answer_callback(callback, "⚠️ خطأ في البيانات.", show_alert=True)
        await state.clear()
        return

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    broadcast_notice = (
        f"🚨 <b>تنبيه هام وعاجل من إدارة المتجر!</b>\n\n"
        f"📢 نود إعلامكم أنه سيتم تحديث وتغيير أسعار جميع باقات الألعاب (فري فاير وببجي) تلقائياً بعد <b>{hours_val:.0f} ساعات</b> من الآن!\n\n"
        f"⚡ <b>لحق اشحن رصيدك واشتري باقاتك فوراً بالأسعار القديمة مباشرة من المحفظة قبل تطبيق الأسعار الجديدة!</b> 💎🎮"
    )

    success_cnt = 0
    for (u_id,) in users:
        try:
            builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💳 شحن الرصيد والشراء الآن", callback_data="main_menu"))
            await bot.send_message(chat_id=u_id, text=broadcast_notice, reply_markup=builder.as_markup())
            success_cnt += 1
            await asyncio.sleep(0.04)
        except:
            pass

    asyncio.create_task(run_full_scheduled_price_update(new_prices_map, hours_val))

    try:
        await callback.message.edit_text(
            f"✅ <b>تمت العملية بنجاح!</b>\n\n"
            f"• تم إرسال الإشعار التنبيهي لـ <b>{success_cnt}</b> مستخدم.\n"
            f"• سيقوم البوت بتطبيق الأسعار الجديدة أوتوماتيكياً في المتجر بعد <b>{hours_val} ساعات</b> بالضبط."
        )
    except:
        pass
        
    await state.clear()
    await safe_answer_callback(callback)

async def run_full_scheduled_price_update(new_prices_map, hours):
    await asyncio.sleep(hours * 3600)
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        for p_key, new_egp in new_prices_map.items():
            cursor.execute("UPDATE product_prices SET price_egp = ? WHERE product_key = ?", (new_egp, p_key))
        conn.commit()
        conn.close()

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⏰ <b>تم تطبيق تحديث الأسعار الشامل التلقائي بنجاح في المتجر!</b>\nتم تحديث أسعار كافة باقات فري فاير وببجي المحددة."
        )
    except Exception as e:
        logging.error(f"Error executing full scheduled price update: {e}")

# ==================== OTHER COMMANDS & CALLBACKS ====================

@router.message(Command("seller"))
async def cmd_seller(message: types.Message):
    user_id = message.from_user.id
    if not is_user_seller(user_id):
        await message.answer("⚠️ You are not an authorized seller.")
        return
    seller_bal, pending_bal, sales_cnt, _, _, _ = get_seller_data(user_id)
    msg = f"🛠️ Seller Control Panel:\nTotal Sales: {sales_cnt}\nAvailable Balance: {seller_bal:.2f} EGP\n⏳ Pending Escrow Balance: {pending_bal:.2f} EGP"
    await message.answer(msg, reply_markup=get_seller_keyboard(user_id))

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    user_username = f"@{message.from_user.username}" if message.from_user.username else "N/A"

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    is_existing_user = cursor.fetchone()
    conn.close()

    save_user(user_id, user_name, user_username)
    balance = get_user_balance(user_id)

    if not is_existing_user:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL_ID,
                text=f"👤 <b>New User Joined!</b>\n\nName: {user_name}\nUsername: {user_username}\nID: <code>{user_id}</code>"
            )
        except Exception:
            pass

    welcome_text = (
        f"Welcome <b>{user_name}</b> to <b>Gk Games</b> Store 🎮\n\n"
        f"Current Balance: <b>{balance:.2f} EGP (~${balance/USDT_EGP_RATE:.2f} USDT)</b> 💳\n\n"
        f"Please choose an option from the menu below:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(user_id))

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await show_faq_msg(message)

@router.message(Command("support"))
async def cmd_support(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💬 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    await message.answer(
        f"🎧 <b>Customer Support:</b>\n\nFor any inquiries or assistance, click the button below to message support directly:",
        reply_markup=builder.as_markup()
    )

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = message.from_user
    bal = get_user_balance(user.id)
    txt = f"👤 Account Info:\nName: {user.full_name}\nID: <code>{user.id}</code>\nBalance: {bal:.2f} EGP (~${bal/USDT_EGP_RATE:.2f} USDT)"
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    await message.answer(txt, reply_markup=builder.as_markup())

@router.message(Command("deposit"))
async def cmd_deposit(message: types.Message, state: FSMContext):
    await state.set_state(DepositState.waiting_for_deposit_amount)
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="💵 200 EGP (~$4)", callback_data="dep_amt_200"),
        types.InlineKeyboardButton(text="💵 500 EGP (~$10)", callback_data="dep_amt_500")
    )
    builder.row(
        types.InlineKeyboardButton(text="💵 1000 EGP (~$20)", callback_data="dep_amt_1000"),
        types.InlineKeyboardButton(text="💵 2000 EGP (~$40)", callback_data="dep_amt_2000")
    )
    msg = (
        "💳 <b>Deposit & Top-up Balance:</b>\n\n"
        f"Minimum deposit limit: <b>{MIN_DEPOSIT_AMOUNT:.0f} EGP (~${MIN_DEPOSIT_AMOUNT/USDT_EGP_RATE:.1f} USDT)</b>\n"
        "🔸 No upper limit! You can deposit any amount you want.\n\n"
        "Choose a preset amount or type the amount directly in chat:"
    )
    await message.answer(msg, reply_markup=builder.as_markup())

@router.callback_query(F.data == "quick_search_id")
async def start_quick_search_id(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuickSearchState.waiting_for_player_id)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))
    try:
        await callback.message.edit_text(
            "🔍 <b>Quick Search by Player ID:</b>\n\n"
            "Please send your **In-Game Player ID** in chat now:",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.message(QuickSearchState.waiting_for_player_id)
async def process_player_id_search(message: types.Message, state: FSMContext):
    player_id = message.text.strip() if message.text else ""
    if not player_id:
        await message.answer("❌ Please send a valid Player ID.")
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Free Fire Packages", callback_data="cat_freefire"))
    builder.row(types.InlineKeyboardButton(text="🎮 PUBG Mobile Packages", callback_data="cat_pubg"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))

    msg = (
        f"✅ <b>Player ID Registered:</b> <code>{player_id}</code>\n\n"
        "Select game category to view available top-up packages:"
    )
    await message.answer(msg, reply_markup=builder.as_markup())
    await state.clear()

@router.callback_query(F.data == "admin_panel_btn")
async def open_admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await safe_answer_callback(callback, "⚠️ Unauthorized!", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "👑 Admin Control Panel:\n\nSelect an action:",
            reply_markup=get_admin_keyboard()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "upgrade_to_seller")
async def process_upgrade_to_seller(callback: types.CallbackQuery):
    user = callback.from_user
    user_id = user.id
    balance = get_user_balance(user_id)
    username_str = f"@{user.username}" if user.username else "No Username"

    if balance < SELLER_UPGRADE_COST_EGP:
        await safe_answer_callback(callback, f"⚠️ Your balance ({balance:.2f} EGP) is not enough to upgrade (Cost: {SELLER_UPGRADE_COST_EGP} EGP).", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ?, is_seller = 1 WHERE user_id = ?", (SELLER_UPGRADE_COST_EGP, user_id))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"⭐ <b>New Seller Subscribed!</b>\n\n"
                f"👤 Name: <b>{user.full_name}</b>\n"
                f"🔗 Username: <b>{username_str}</b>\n"
                f"🆔 ID: <code>{user_id}</code>\n"
                f"💰 Deducted Amount: <b>{SELLER_UPGRADE_COST_EGP:.2f} EGP</b>"
            )
        )
    except Exception:
        pass

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))

    try:
        await callback.message.edit_text("⭐ Your account has been successfully upgraded to Seller.", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_panel_btn")
async def open_seller_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id):
        await safe_answer_callback(callback, "⚠️ Unauthorized!", show_alert=True)
        return

    seller_bal, pending_bal, sales_cnt, _, _, _ = get_seller_data(user_id)
    msg = f"🛠️ Seller Control Panel:\nTotal Sales: {sales_cnt}\nAvailable Balance: {seller_bal:.2f} EGP\n⏳ Pending Escrow Balance: {pending_bal:.2f} EGP"
    try:
        await callback.message.edit_text(msg, reply_markup=get_seller_keyboard(user_id))
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_add_stock")
async def seller_add_stock_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Free Fire Stock", callback_data="addstock_cat_ff"))
    builder.row(types.InlineKeyboardButton(text="🎮 PUBG Mobile Stock", callback_data="addstock_cat_pubg"))
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))

    try:
        await callback.message.edit_text("📦 Choose game category to add stock:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "addstock_cat_ff")
async def addstock_freefire_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return

    builder = InlineKeyboardBuilder()
    ff_items = ["ff110", "ff231", "ff583", "ff1188", "ff2420"]
    for p_key in ff_items:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        price_egp, _ = get_product_prices(p_key)
        builder.row(types.InlineKeyboardButton(text=f"🔥 {title} ({price_egp} EGP)", callback_data=f"select_add_p_{p_key}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="seller_add_stock"))

    try:
        await callback.message.edit_text("🔥 Select Free Fire package:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "addstock_cat_pubg")
async def addstock_pubg_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return

    builder = InlineKeyboardBuilder()
    pubg_items = ["pubg60", "pubg325", "pubg660", "pubg1800", "pubg3850", "pubg8100"]
    for p_key in pubg_items:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        price_egp, _ = get_product_prices(p_key)
        builder.row(types.InlineKeyboardButton(text=f"🎮 {title} ({price_egp} EGP)", callback_data=f"select_add_p_{p_key}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="seller_add_stock"))

    try:
        await callback.message.edit_text("🎮 Select PUBG Mobile package:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("select_add_p_"))
async def select_package_for_stock(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return

    p_key = callback.data.split("_")[3]
    prod_title = PRODUCTS_TITLES.get(p_key, p_key)

    await state.update_data(stock_product_key=p_key, stock_is_admin=0)
    await state.set_state(SellerState.waiting_for_seller_stock)

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="seller_panel_btn"))

    msg = (
        f"📦 Selected Package: <b>{prod_title}</b>\n\n"
        "📲 Send codes now (each code on a separate line).\n"
        "✨ Codes will be added to inventory instantly."
    )
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_addstock")
async def admin_add_stock_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Free Fire", callback_data="adm_stock_ff"))
    builder.row(types.InlineKeyboardButton(text="🎮 PUBG Mobile", callback_data="adm_stock_pubg"))
    builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))

    try:
        await callback.message.edit_text("👑 Admin Stock - Choose category:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_stock_ff")
async def adm_stock_ff(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    for p_key in ["ff110", "ff231", "ff583", "ff1188", "ff2420"]:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        builder.row(types.InlineKeyboardButton(text=f"🔥 {title}", callback_data=f"adm_sel_p_{p_key}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="adm_addstock"))
    try:
        await callback.message.edit_text("🔥 Select Free Fire package:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_stock_pubg")
async def adm_stock_pubg(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    builder = InlineKeyboardBuilder()
    for p_key in ["pubg60", "pubg325", "pubg660", "pubg1800", "pubg3850", "pubg8100"]:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        builder.row(types.InlineKeyboardButton(text=f"🎮 {title}", callback_data=f"adm_sel_p_{p_key}"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="adm_addstock"))
    try:
        await callback.message.edit_text("🎮 Select PUBG package:", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_sel_p_"))
async def adm_select_package(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    p_key = callback.data.split("_")[3]
    prod_title = PRODUCTS_TITLES.get(p_key, p_key)

    await state.update_data(stock_product_key=p_key, stock_is_admin=1)
    await state.set_state(SellerState.waiting_for_seller_stock)

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    msg = (
        f"👑 Admin Stock - <b>{prod_title}</b>\n\n"
        "📲 Send codes now (each on a new line, added instantly):"
    )
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_edit_prices_menu")
async def adm_edit_prices_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    builder = InlineKeyboardBuilder()
    for p_key, title in PRODUCTS_TITLES.items():
        egp_p, usdt_p = get_product_prices(p_key)
        builder.row(types.InlineKeyboardButton(text=f"✏️ {title} ({egp_p} EGP | ${usdt_p})", callback_data=f"adm_set_price_{p_key}"))
        
    builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    
    try:
        await callback.message.edit_text("✏️ <b>Select a product to update its prices (EGP & USDT):</b>", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_set_price_"))
async def adm_set_price_select(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    p_key = callback.data.split("_")[3]
    prod_title = PRODUCTS_TITLES.get(p_key, p_key)
    
    await state.update_data(editing_product_key=p_key)
    await state.set_state(AdminState.waiting_for_new_price_egp)
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="adm_edit_prices_menu"))
    try:
        egp_p, usdt_p = get_product_prices(p_key)
        await callback.message.edit_text(
            f"📦 Product: <b>{prod_title}</b>\n"
            f"Current EGP Price: <b>{egp_p} EGP</b> | Current USDT: <b>${usdt_p}</b>\n\n"
            f"✍️ Step 1: Send the new price in **Egyptian Pounds (EGP)** (e.g., `45`):",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_new_price_egp)
async def adm_save_new_price_egp(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        new_egp = float(message.text.strip())
        if new_egp < 0:
            await message.answer("❌ Price cannot be negative.")
            return
        await state.update_data(new_egp_val=new_egp)
        await state.set_state(AdminState.waiting_for_new_price_usdt)
        
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="adm_edit_prices_menu"))
        await message.answer("✍️ Step 2: Send the new price in **USDT (Dollar)** (e.g., `0.90` or `5.0`):", reply_markup=builder.as_markup())
    except ValueError:
        await message.answer("❌ Invalid format. Please send a valid number for EGP price:")

@router.message(AdminState.waiting_for_new_price_usdt)
async def adm_save_new_price_usdt(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    p_key = data.get("editing_product_key")
    new_egp = data.get("new_egp_val")
    
    try:
        new_usdt = float(message.text.strip())
        if new_usdt < 0:
            await message.answer("❌ Price cannot be negative.")
            return
            
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE product_prices SET price_egp = ?, price_usdt = ? WHERE product_key = ?", (new_egp, new_usdt, p_key))
        conn.commit()
        conn.close()
        
        prod_title = PRODUCTS_TITLES.get(p_key, p_key)
        await message.answer(f"✅ Successfully updated <b>{prod_title}</b>:\n• EGP Price: <b>{new_egp} EGP</b>\n• USDT Price: <b>${new_usdt} USDT</b>")
        await state.clear()
    except ValueError:
        await message.answer("❌ Invalid format. Please send a valid number for USDT price:")

@router.message(SellerState.waiting_for_seller_stock)
async def process_bulk_stock_items(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_key = data.get("stock_product_key")
    is_admin = data.get("stock_is_admin", 0)
    user_id = message.from_user.id

    if not message.text:
        await message.answer("❌ يرجى إرسال نص يحتوي على الأكواد.")
        return

    if not p_key:
        await message.answer("❌ خطأ: لم يتم التعرف على الباقة. يرجى البدء من جديد.")
        await state.clear()
        return

    lines = message.text.strip().split("\n")
    success_count = 0
    duplicate_count = 0
    invalid_format_count = 0

    price_egp, _ = get_product_prices(p_key)
    is_freefire = p_key.startswith("ff")

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()

    for line in lines:
        code = line.strip()
        if not code:
            continue

        if is_freefire and not (code.isdigit() and len(code) == 16):
            invalid_format_count += 1
            continue

        try:
            cursor.execute("SELECT id FROM stock WHERE code = ?", (code,))
            if cursor.fetchone():
                duplicate_count += 1
                continue
            
            s_id = 0 if is_admin == 1 else user_id
            cursor.execute("INSERT INTO stock (product_key, code, seller_id, price, status) VALUES (?, ?, ?, ?, 'active')", (p_key, code, s_id, price_egp))
            success_count += 1
        except sqlite3.IntegrityError:
            duplicate_count += 1
        except:
            pass

    conn.commit()
    conn.close()

    prod_name = PRODUCTS_TITLES.get(p_key, p_key)
    
    reply_msg = f"✅ <b>نتائج إضافة الستوك ({prod_name}):</b>\n\n"
    reply_msg += f"• تم الإضافة بنجاح: <b>{success_count}</b>\n"
    reply_msg += f"• أكواد مكررة تم تجاهلها: <b>{duplicate_count}</b>\n"
    if invalid_format_count > 0:
        reply_msg += f"❌ <b>أكواد مرفوضة (ليست 16 رقم): {invalid_format_count}</b>\nسبب الرفض: كود فري فاير يجب أن يتكون من 16 رقمًا بالضبط."

    await message.answer(reply_msg)
    
    if success_count > 0:
        asyncio.create_task(notify_subscribed_users_new_stock(p_key, success_count))
        if is_admin != 1:
            try:
                await bot.send_message(chat_id=ADMIN_ID, text=f"🔔 البائع (ID: <code>{user_id}</code>) أضاف <b>{success_count}</b> كود للباقة <b>{prod_name}</b>.")
            except:
                pass
                
    await state.clear()

@router.callback_query(F.data == "adm_stock_overview")
async def admin_stock_overview(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    
    msg = "📊 <b>Available Stock Summary:</b>\n\n"
    for p_key, title in PRODUCTS_TITLES.items():
        cursor.execute("SELECT COUNT(*) FROM stock WHERE product_key = ? AND status = 'active'", (p_key,))
        cnt = cursor.fetchone()[0]
        status_icon = "🔴 (Low)" if cnt < 3 else ("🟡 (Medium)" if cnt < 10 else "🟢 (Available)")
        msg += f"• {title}: <b>{cnt}</b> codes {status_icon}\n"
        
    conn.close()
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_view_all_codes")
async def admin_view_all_codes_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_key, code, seller_id FROM stock WHERE status = 'active' ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    if not rows:
        msg = "ℹ️ No active stock codes found in database."
    else:
        msg = f"📋 <b>Active Stock Codes (Showing latest {len(rows)}):</b>\n\n"
        for st_id, p_key, code_val, s_id in rows:
            p_title = PRODUCTS_TITLES.get(p_key, p_key)
            owner_str = "Admin 👑" if s_id == 0 else f"Seller ID {s_id}"
            msg += f"• [{p_title}] <code>{code_val}</code> ({owner_str})\n"
            builder.row(types.InlineKeyboardButton(text=f"🗑️ Delete [{p_title} | {code_val}]", callback_data=f"adm_del_any_st_{st_id}"))

    builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_del_any_st_"))
async def admin_delete_any_stock_code(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    st_id = int(callback.data.split("_")[4])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock WHERE id = ?", (st_id,))
    conn.commit()
    conn.close()
    await safe_answer_callback(callback, "✅ Code deleted successfully.", show_alert=True)
    await admin_view_all_codes_handler(callback)

@router.callback_query(F.data == "adm_net_profits")
async def admin_net_profits_report(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    def calc_profits(date_filter=None):
        query = "SELECT seller_id, price, net_profit FROM purchased_transactions WHERE is_refunded = 0"
        params = []
        if date_filter:
            if "%" in date_filter:
                query += " AND date_time LIKE ?"
            else:
                query += " AND date_time >= ?"
            params.append(date_filter)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        commission_profits = 0.0
        direct_admin_profits = 0.0
        
        for seller_id, price, n_profit in rows:
            if seller_id == 0:
                direct_admin_profits += price
            else:
                sales_cnt = get_seller_data(seller_id)[2]
                fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
                commission_profits += (price * fee_rate)
                
        return commission_profits, direct_admin_profits

    comm_today, direct_today = calc_profits(f"{today_str}%")
    comm_week, direct_week = calc_profits(week_ago)
    comm_month, direct_month = calc_profits(month_ago)
    
    conn.close()

    msg = (
        f"💎 <b>Net Profit Report:</b>\n\n"
        f"📅 <b>Today's Profits:</b>\n"
        f"• Seller Commissions: <b>{comm_today:.2f} EGP</b>\n"
        f"• Admin Direct Stock: <b>{direct_today:.2f} EGP</b>\n"
        f"💰 <b>Total Net Today: {comm_today + direct_today:.2f} EGP (~${(comm_today + direct_today)/USDT_EGP_RATE:.2f} USDT)</b>\n\n"
        f"📆 <b>Last 7 Days:</b>\n"
        f"• Seller Commissions: <b>{comm_week:.2f} EGP</b>\n"
        f"• Admin Direct Stock: <b>{direct_week:.2f} EGP</b>\n"
        f"💰 <b>Total Net Week: {comm_week + direct_week:.2f} EGP (~${(comm_week + direct_week)/USDT_EGP_RATE:.2f} USDT)</b>\n\n"
        f"🗓️ <b>Last 30 Days:</b>\n"
        f"• Seller Commissions: <b>{comm_month:.2f} EGP</b>\n"
        f"• Admin Direct Stock: <b>{direct_month:.2f} EGP</b>\n"
        f"💰 <b>Total Net Month: {comm_month + direct_month:.2f} EGP (~${(comm_month + direct_month)/USDT_EGP_RATE:.2f} USDT)</b>"
    )

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "adm_sales_analytics")
async def admin_sales_analytics(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_name, COUNT(*), SUM(price) 
        FROM purchased_transactions 
        WHERE is_refunded = 0 
        GROUP BY product_name 
        ORDER BY COUNT(*) DESC LIMIT 5
    """)
    top_products = cursor.fetchall()

    cursor.execute("""
        SELECT seller_id, COUNT(*), SUM(price) 
        FROM purchased_transactions 
        WHERE seller_id > 0 AND is_refunded = 0 
        GROUP BY seller_id 
        ORDER BY COUNT(*) DESC
    """)
    seller_stats = cursor.fetchall()
    
    conn.close()

    msg = "📈 <b>Sales Analytics Overview:</b>\n\n"
    msg += "🔥 <b>Top Selling Products:</b>\n"
    if top_products:
        for p_name, count, total_vol in top_products:
            msg += f"• <b>{p_name}</b>: Sold <b>{count}</b> times (Total: <b>{total_vol:.2f} EGP</b>)\n"
    else:
        msg += "ℹ️ No sales recorded yet.\n"

    msg += "\n⭐ <b>Sellers Performance:</b>\n"
    if seller_stats:
        for s_id, count, total_vol in seller_stats:
            s_bal, pending_bal, s_sales, _, s_name, s_uname = get_seller_data(s_id)
            fee_rate = VIP_PLATFORM_FEE if s_sales >= 50 else DEFAULT_PLATFORM_FEE
            store_comm = total_vol * fee_rate
            seller_net = total_vol - store_comm
            msg += (
                f"👤 <b>{s_name}</b> (@{s_uname} | ID: <code>{s_id}</code>)\n"
                f"   - Sales: <b>{count}</b>\n"
                f"   - Volume: <b>{total_vol:.2f} EGP</b>\n"
                f"   - Seller Net: <b>{seller_net:.2f} EGP</b>\n"
                f"   - Store Commission: <b>{store_comm:.2f} EGP</b>\n"
                f"--------------------\n"
            )
    else:
        msg += "ℹ️ No seller sales recorded yet.\n"

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("remove_stock_"))
async def seller_remove_single_code(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): 
        await safe_answer_callback(callback, "⚠️ Unauthorized!", show_alert=True)
        return
        
    stock_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM stock WHERE id = ? AND seller_id = ?", (stock_id, user_id))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        await safe_answer_callback(callback, "❌ Code not found or already removed.", show_alert=True)
        return
        
    cursor.execute("DELETE FROM stock WHERE id = ?", (stock_id,))
    conn.commit()
    conn.close()
    
    await safe_answer_callback(callback, f"✅ Code removed successfully.", show_alert=True)
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_key, code, price FROM stock WHERE seller_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    if rows:
        for s_id, p_key, code_val, price in rows:
            prod_name = PRODUCTS_TITLES.get(p_key, p_key)
            builder.row(types.InlineKeyboardButton(text=f"🗑️ Remove [{prod_name} | {code_val}]", callback_data=f"remove_stock_{s_id}"))
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    
    msg = f"📋 Your Current Stock ({len(rows)} items):" if rows else "ℹ️ No codes found in your stock."
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass

@router.callback_query(F.data == "seller_view_my_stock")
async def seller_view_my_stock_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_key, code, price FROM stock WHERE seller_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    if rows:
        for s_id, p_key, code_val, price in rows:
            prod_name = PRODUCTS_TITLES.get(p_key, p_key)
            builder.row(types.InlineKeyboardButton(text=f"🗑️ Remove [{prod_name} | {code_val}]", callback_data=f"remove_stock_{s_id}"))
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))

    msg = f"📋 Your Current Stock ({len(rows)} items):" if rows else "ℹ️ No codes found in your stock."
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_sales_history")
async def seller_sales_history_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, game_code, price, date_time, escrow_released FROM purchased_transactions WHERE seller_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📊 <b>Your Sales History:</b>\n\nℹ️ No sales recorded yet."
    else:
        msg = f"📊 <b>Your Sales History ({len(rows)} items):</b>\n\n"
        for p_name, g_code, price, d_time, released in rows:
            status_escrow = "🟢 Released" if released == 1 else "⏳ Pending Escrow"
            msg += f"📦 Product: <b>{p_name}</b>\n🔑 Code: <code>{g_code}</code>\n💰 Price: <b>{price} EGP</b>\n📋 Escrow: <b>{status_escrow}</b>\n📅 Date: <i>{d_time}</i>\n--------------------\n"

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_financial_ledger")
async def seller_financial_ledger_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_user_seller(user_id): return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, amount, details, status, date_time FROM seller_withdrawals WHERE seller_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📜 <b>Your Financial Ledger (Withdrawals):</b>\n\nℹ️ No withdrawal requests found."
    else:
        msg = f"📜 <b>Your Financial Ledger ({len(rows)} requests):</b>\n\n"
        for w_id, amount, details, status, d_time in rows:
            status_str = "🟢 Approved" if status == 'approved' else ("🔴 Rejected" if status == 'rejected' else "⏳ Pending")
            msg += f"🆔 Request #{w_id}\n💰 Amount: <b>{amount:.2f} EGP</b>\n📋 Status: <b>{status_str}</b>\n📅 Date: <i>{d_time}</i>\n--------------------\n"

    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_balance_menu")
async def seller_balance_options(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    seller_bal, pending_bal, _, _, _, _ = get_seller_data(user_id)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💸 Request Profit Withdrawal", callback_data="seller_withdraw_request"))
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    try:
        await callback.message.edit_text(
            f"💰 Available Balance: <b>{seller_bal:.2f} EGP (~${seller_bal/USDT_EGP_RATE:.2f} USDT)</b>\n"
            f"⏳ Pending Escrow Balance: <b>{pending_bal:.2f} EGP</b>\n\n"
            f"(Minimum withdrawal limit: <b>{SELLER_MIN_WITHDRAW} EGP</b>)", 
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_withdraw_request")
async def seller_withdraw_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    seller_bal, _, _, _, _, _ = get_seller_data(user_id)
    if seller_bal < SELLER_MIN_WITHDRAW:
        await safe_answer_callback(callback, f"⚠️ Available balance is less than minimum limit ({SELLER_MIN_WITHDRAW} EGP). Note: Pending escrow balance cannot be withdrawn until released.", show_alert=True)
        return
    await state.set_state(SellerWithdrawState.waiting_for_seller_withdraw)
    try:
        await callback.message.edit_text(
            f"💰 Available Balance: <b>{seller_bal:.2f} EGP</b>\n\n"
            f"Send withdrawal amount and payout details (e.g., `300 01012345678` or `50 CryptoAddress`):\n"
            f"(Minimum limit: <b>{SELLER_MIN_WITHDRAW} EGP</b>)"
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.message(SellerWithdrawState.waiting_for_seller_withdraw)
async def seller_withdraw_finish(message: types.Message, state: FSMContext):
    user = message.from_user
    seller_bal, _, _, _, _, _ = get_seller_data(user.id)

    try:
        text_val = message.text.strip()
        parts = text_val.split(maxsplit=1)
        withdraw_amount = float(parts[0])
        details = parts[1] if len(parts) > 1 else ""

        if withdraw_amount < SELLER_MIN_WITHDRAW:
            await message.answer(f"⚠️ Minimum withdrawal limit is {SELLER_MIN_WITHDRAW} EGP.")
            return

        if withdraw_amount > seller_bal:
            await message.answer(f"⚠️ Requested amount exceeds available balance ({seller_bal:.2f} EGP).")
            return

        if not details:
            await message.answer("📲 Please include payout details (e.g., `500 VodafoneCash` or `10 CryptoAddress`):")
            return

    except ValueError:
        await message.answer("❌ Invalid format. Please enter amount and details correctly (e.g., `300 010xxxxxxxx`):")
        return

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO seller_withdrawals (seller_id, amount, details, status, date_time) VALUES (?, ?, ?, 'pending', ?)", (user.id, withdraw_amount, details, current_time))
    w_id = cursor.lastrowid
    cursor.execute("UPDATE users SET seller_balance = seller_balance - ? WHERE user_id = ?", (withdraw_amount, user.id))
    conn.commit()
    conn.close()

    await message.answer("✅ Withdrawal request submitted successfully! Pending admin approval.")
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ موافقة وتحويل الفلوس", callback_data=f"adm_app_w_{w_id}_{user.id}_{withdraw_amount}"),
        types.InlineKeyboardButton(text="❌ رفض الطلب وإرجاع المبلغ", callback_data=f"adm_rej_w_{w_id}_{user.id}_{withdraw_amount}")
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID, 
        text=f"💸 <b>New Withdrawal Request #{w_id}</b>\nAmount: <b>{withdraw_amount:.2f} EGP</b>\nSeller: {user.full_name} (ID: <code>{user.id}</code>)\nDetails: <code>{details}</code>",
        reply_markup=builder.as_markup()
    )
    await state.clear()

@router.callback_query(F.data.startswith("adm_app_w_"))
async def admin_approve_withdrawal(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    w_id = int(parts[3])
    seller_id = int(parts[4])
    amount = float(parts[5])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE seller_withdrawals SET status = 'approved' WHERE id = ?", (w_id,))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=seller_id, text=f"✅ Your withdrawal request of <b>{amount:.2f} EGP</b> has been approved and processed successfully!")
    except:
        pass
    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Approved & Transferred.")
    except:
        pass
    await safe_answer_callback(callback, "Approved successfully.")

@router.callback_query(F.data.startswith("adm_rej_w_"))
async def admin_reject_withdrawal(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    w_id = int(parts[3])
    seller_id = int(parts[4])
    amount = float(parts[5])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET seller_balance = seller_balance + ? WHERE user_id = ?", (amount, seller_id))
    cursor.execute("UPDATE seller_withdrawals SET status = 'rejected' WHERE id = ?", (w_id,))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=seller_id, text=f"❌ Your withdrawal request was rejected by admin and <b>{amount:.2f} EGP</b> returned to your available balance.")
    except:
        pass
    try:
        await callback.message.edit_text(callback.message.text + "\n\n❌ Rejected.")
    except:
        pass
    await safe_answer_callback(callback, "Rejected successfully.")

@router.callback_query(F.data == "adm_pending_orders")
async def show_pending_orders(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await safe_answer_callback(callback, "⚠️ Unauthorized!", show_alert=True)
        return

    orders = get_all_pending_orders()
    if not orders:
        msg = "ℹ️ No pending orders at the moment."
    else:
        msg = f"⏳ Pending Orders ({len(orders)} orders):\n\n"
        for order_id, user_id, product_title, username, p_type in orders:
            msg += f"Order #{order_id} | Type: {p_type}\nProduct: {product_title}\nUser: {username} (ID: <code>{user_id}</code>)\n--------------------\n"

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))

    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

# ==================== DEPOSIT SYSTEM ====================

@router.callback_query(F.data == "deposit_balance")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DepositState.waiting_for_deposit_amount)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="💵 200 EGP (~$4)", callback_data="dep_amt_200"),
        types.InlineKeyboardButton(text="💵 500 EGP (~$10)", callback_data="dep_amt_500")
    )
    builder.row(
        types.InlineKeyboardButton(text="💵 1000 EGP (~$20)", callback_data="dep_amt_1000"),
        types.InlineKeyboardButton(text="💵 2000 EGP (~$40)", callback_data="dep_amt_2000")
    )
    builder.row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))

    msg = (
        "💳 <b>Deposit & Top-up Wallet:</b>\n\n"
        f"🔸 Minimum Deposit Limit: <b>{MIN_DEPOSIT_AMOUNT:.0f} EGP (~${MIN_DEPOSIT_AMOUNT/USDT_EGP_RATE:.1f} USDT)</b>\n"
        "🔸 No upper limit! You can deposit any amount you want.\n\n"
        "Select a preset amount or **type the amount directly in chat**:"
    )
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("dep_amt_"))
async def process_preset_deposit_amount(callback: types.CallbackQuery, state: FSMContext):
    amount = float(callback.data.split("_")[2])
    usdt_val = amount / USDT_EGP_RATE
    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositState.waiting_for_deposit_receipt)
    
    msg = (
        f"✅ Selected Deposit Amount: <b>{amount:.0f} EGP (~${usdt_val:.2f} USDT)</b>\n\n"
        f"📲 <b>Payment Methods Available:</b>\n\n"
        f"🇪🇬 <b>Vodafone Cash (Egypt):</b>\n"
        f"• Number: <code>{VODAFONE_NUMBER}</code> (Tap to copy)\n\n"
        f"🌐 <b>Binance USDT (TRC20 Network):</b>\n"
        f"• Address: <code>{USDT_TRC20_ADDRESS}</code> (Tap to copy)\n\n"
        "📸 <b>Required Verification Steps:</b>\n"
        "1. Send transfer receipt screenshot photo.\n"
        "2. Include <b>TXID / Order ID</b> (for Crypto) OR <b>Phone Number</b> (for Vodafone Cash)."
    )
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        await callback.message.answer(msg, reply_markup=builder.as_markup())
    await safe_answer_callback(callback)

@router.message(DepositState.waiting_for_deposit_amount)
async def deposit_check_amount(message: types.Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("❌ Please enter a valid numerical amount.")
            return
        amount = float(message.text.strip())
        if amount < MIN_DEPOSIT_AMOUNT:
            await message.answer(f"⚠️ Minimum deposit limit is {MIN_DEPOSIT_AMOUNT:.0f} EGP:")
            return
            
        usdt_val = amount / USDT_EGP_RATE
        await state.update_data(deposit_amount=amount)
        await state.set_state(DepositState.waiting_for_deposit_receipt)
        
        msg = (
            f"✅ Selected Deposit Amount: <b>{amount:.0f} EGP (~${usdt_val:.2f} USDT)</b>\n\n"
            f"📲 <b>Payment Methods Available:</b>\n\n"
            f"🇪🇬 <b>Vodafone Cash (Egypt):</b>\n"
            f"• Number: <code>{VODAFONE_NUMBER}</code> (Tap to copy)\n\n"
            f"🌐 <b>Binance USDT (TRC20 Network):</b>\n"
            f"• Address: <code>{USDT_TRC20_ADDRESS}</code> (Tap to copy)\n\n"
            "📸 <b>Required Verification Steps:</b>\n"
            "Send transfer receipt screenshot photo now."
        )
        await message.answer(msg)
    except ValueError:
        await message.answer("❌ Invalid amount format. Please send digits only.")

@router.message(DepositState.waiting_for_deposit_receipt, F.photo)
async def deposit_receive_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dep_amount = data.get("deposit_amount", 0.0)
    photo_id = message.photo[-1].file_id
    
    details = message.caption.strip() if message.caption else "No details attached"
    user = message.from_user

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO active_deposits (user_id, amount, details, receipt_file_id, status) VALUES (?, ?, ?, ?, 'pending')",
        (user.id, dep_amount, details, photo_id)
    )
    deposit_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await message.answer("✅ <b>Deposit request submitted!</b>\nAdmin is reviewing your transaction and balance will be updated shortly.")
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Approve Deposit", callback_data=f"accept_dep_{deposit_id}_{user.id}_{int(dep_amount)}"),
        types.InlineKeyboardButton(text="❌ Reject Deposit", callback_data=f"reject_dep_{deposit_id}_{user.id}")
    )

    admin_notice = (
        f"💳 <b>New Deposit Request #{deposit_id}</b>\n\n"
        f"💰 Amount: <b>{dep_amount:.2f} EGP (~${dep_amount/USDT_EGP_RATE:.2f} USDT)</b>\n"
        f"👤 User: {user.full_name} (@{user.username if user.username else 'NoUsername'} | ID: <code>{user.id}</code>)\n"
        f"📝 Sender Info / TXID: <code>{details}</code>"
    )
    
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_notice, reply_markup=builder.as_markup())
    except:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_notice, reply_markup=builder.as_markup())
        
    await state.clear()

@router.callback_query(F.data.startswith("accept_dep_"))
async def admin_accept_deposit(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    deposit_id = int(parts[2])
    target_user_id = int(parts[3])
    amount = float(parts[4])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
    cursor.execute("DELETE FROM active_deposits WHERE deposit_id = ?", (deposit_id,))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=target_user_id, text=f"✅ Deposit accepted by admin.\nAdded <b>{amount:.2f} EGP</b> to your balance.")
    except:
        pass

    try:
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ Accepted and credited.", reply_markup=None)
    except:
        pass
    await safe_answer_callback(callback, "✅ Deposit accepted.")

@router.callback_query(F.data.startswith("reject_dep_"))
async def admin_reject_deposit(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    deposit_id = int(parts[2])
    target_user_id = int(parts[3])

    await state.update_data(reject_dep_id=deposit_id, reject_target_user=target_user_id)
    await state.set_state(AdminState.waiting_for_deposit_reject)
    await callback.message.reply("✍️ Enter reject reason:")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_deposit_reject)
async def admin_send_deposit_reject_reason(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    deposit_id = data.get("reject_dep_id")
    target_user_id = data.get("reject_target_user")
    reason = message.text.strip() if message.text else "No reason provided"

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_deposits WHERE deposit_id = ?", (deposit_id,))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=target_user_id, text=f"❌ Deposit rejected.\nReason: {reason}")
        await message.reply(f"🚫 Deposit #{deposit_id} rejected.")
    except:
        pass
    await state.clear()

# ==================== ORDER FLOW & PURCHASES ====================

@router.callback_query(F.data.startswith("sub_stock_"))
async def subscribe_stock_notification(callback: types.CallbackQuery):
    p_key = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO stock_subscriptions (user_id, product_key) VALUES (?, ?)", (user_id, p_key))
        conn.commit()
        await safe_answer_callback(callback, "🔔 You will receive a notification as soon as stock arrives!", show_alert=True)
    except sqlite3.IntegrityError:
        await safe_answer_callback(callback, "ℹ️ You are already subscribed for stock alerts on this item.", show_alert=True)
    conn.close()

@router.callback_query(F.data.startswith("buy_"))
async def process_buy_click(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    p_key = parts[1]
    curr = parts[2] if len(parts) > 2 else "egp"
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock WHERE product_key = ? AND status = 'active'", (p_key,))
    stock_count = cursor.fetchone()[0]
    conn.close()

    if stock_count <= 0:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🔔 Notify Me When Available", callback_data=f"sub_stock_{p_key}"))
        builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
        
        try:
            await callback.message.edit_text(
                "⚠️ <b>Out of Stock!</b>\n\nSorry, this item is currently unavailable. Click below to get notified when restocked:",
                reply_markup=builder.as_markup()
            )
        except:
            pass
        await safe_answer_callback(callback)
        return

    title = PRODUCTS_TITLES.get(p_key, "Item")
    egp_price, usdt_price = get_product_prices(p_key)
    
    await state.update_data(product_title=title, product_key=p_key, product_price_egp=egp_price, product_price_usdt=usdt_price, selected_currency=curr)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💳 Pay from Wallet Balance", callback_data="pay_method_wallet"))
    builder.row(types.InlineKeyboardButton(text="📱 Direct Payment / External", callback_data="pay_method_external"))
    builder.row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))
    
    display_price_str = f"{egp_price:.0f} EGP" if curr == "egp" else f"${usdt_price:.2f} USDT"
    try:
        await callback.message.edit_text(
            f"🛒 Selected Product: <b>{title}</b>\n💰 Price: <b>{display_price_str}</b>\n\nChoose payment method:",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "pay_method_wallet")
async def process_pay_wallet_request(callback: types.CallbackQuery, state: FSMContext):
    user = callback.from_user
    user_bal = get_user_balance(user.id)
    data = await state.get_data()
    prod_title = data.get("product_title", "Product")
    prod_key = data.get("product_key", "item")
    price = data.get("product_price_egp", 0.0)

    if user_bal < price:
        await safe_answer_callback(callback, f"❌ Insufficient balance ({user_bal:.2f} EGP). Please deposit first.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user.id))
    conn.commit()
    conn.close()

    auto_code, auto_seller_id, _ = get_stock_code(prod_key)
    if not auto_code:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user.id))
        conn.commit()
        conn.close()
        await safe_answer_callback(callback, "⚠️ Sorry, stock just ran out! Your balance has been refunded.", show_alert=True)
        return

    seller_info_str = "Admin Direct Stock 👑"
    net_profit = 0.0
    if auto_seller_id > 0:
        sales_cnt = get_seller_data(auto_seller_id)[2]
        fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
        store_commission = price * fee_rate
        net_profit = price - store_commission
        
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET seller_pending_balance = seller_pending_balance + ?, seller_sales_count = seller_sales_count + 1 WHERE user_id = ?", (net_profit, auto_seller_id))
        conn.commit()
        conn.close()

        s_bal, pending_bal, s_sales, _, s_name, s_uname = get_seller_data(auto_seller_id)
        s_username_str = f"@{s_uname}" if s_uname and s_uname != "N/A" else "No Username"
        seller_info_str = f"<b>{s_name}</b> ({s_username_str} | ID: <code>{auto_seller_id}</code>)"

        try:
            await bot.send_message(
                chat_id=auto_seller_id, 
                text=f"🎉 <b>One of your stock items was sold!</b>\n\n📦 Product: <b>{prod_title}</b>\n🔑 Code Sold: <code>{auto_code}</code>\n⏳ Net Profit Added to Escrow: <b>{net_profit:.2f} EGP</b> (will be released upon buyer confirmation or after 1 hour)."
            )
        except:
            pass

    trans_id = save_user_purchased_code(user.id, prod_title, auto_code, auto_seller_id, price, net_profit)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ تأكيد شحن الكود بنجاح", callback_data=f"confirm_deliv_{trans_id}"))
    builder.row(types.InlineKeyboardButton(text="🔄 Request Refund", callback_data=f"req_refund_{trans_id}"))

    try:
        await callback.message.edit_text(
            f"✅ <b>Purchase successful!</b>\n\n"
            f"📦 Product: <b>{prod_title}</b>\n"
            f"🔑 Code: <code>{auto_code}</code>\n\n"
            f"👇 اضغط على الزر أدناه لتأكيد شحن الكود وتقييم الخدمة:",
            reply_markup=builder.as_markup()
        )
    except:
        pass

    user_uname_str = f"@{user.username}" if user.username else "No Username"
    admin_sale_notice = (
        f"🛍️ <b>Instant Wallet Order Delivered!</b>\n\n"
        f"👤 <b>Buyer Details:</b>\n"
        f"• Name: <b>{user.full_name}</b>\n"
        f"• Username: <b>{user_uname_str}</b>\n"
        f"• ID: <code>{user.id}</code>\n\n"
        f"📦 <b>Order Info:</b>\n"
        f"• Product: <b>{prod_title}</b>\n"
        f"• Code: <code>{auto_code}</code>\n"
        f"• Price: <b>{price:.2f} EGP</b>\n\n"
        f"🏷️ <b>Seller Source:</b> {seller_info_str}"
    )

    try:
        await bot.send_message(chat_id=DELIVERY_PROOF_CHANNEL_ID, text=f"✅ Instant Wallet Order Delivered.\nProduct: {prod_title}")
        await bot.send_message(chat_id=ADMIN_ID, text=admin_sale_notice)
    except:
        pass

    await state.clear()
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("confirm_deliv_"))
async def process_confirm_delivery(callback: types.CallbackQuery):
    trans_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, net_profit, escrow_released FROM purchased_transactions WHERE id = ? AND user_id = ?", (trans_id, callback.from_user.id))
    row = cursor.fetchone()
    
    if row:
        seller_id, net_profit, released = row
        if released == 0 and seller_id > 0:
            cursor.execute("UPDATE purchased_transactions SET confirmed_delivery = 1, escrow_released = 1 WHERE id = ?", (trans_id,))
            cursor.execute("UPDATE users SET seller_pending_balance = seller_pending_balance - ?, seller_balance = seller_balance + ? WHERE user_id = ?", (net_profit, net_profit, seller_id))
            conn.commit()
            
            try:
                await bot.send_message(chat_id=seller_id, text=f"✅ <b>Escrow Released!</b>\nBuyer confirmed delivery for transaction #{trans_id}. Net profit of <b>{net_profit:.2f} EGP</b> has been moved to your available balance!")
            except:
                pass
        else:
            cursor.execute("UPDATE purchased_transactions SET confirmed_delivery = 1 WHERE id = ?", (trans_id,))
            conn.commit()
            
    conn.close()

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{trans_id}_1"),
        types.InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{trans_id}_2"),
        types.InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{trans_id}_3"),
        types.InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{trans_id}_4"),
        types.InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{trans_id}_5")
    )
    
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>تم تأكيد شحن الكود بنجاح وتحرير الرصيد للبائع!</b>\n\n🌟 يُرجى تقييم تجربتك معنا:",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback, "✅ شكراً لك! تم تأكيد الشحن.", show_alert=True)

@router.callback_query(F.data == "pay_method_external")
async def process_pay_external_request(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr = data.get("selected_currency", "egp")
    egp_price = data.get("product_price_egp", 0.0)
    usdt_price = data.get("product_price_usdt", 0.0)

    await state.update_data(payment_type="external")
    await state.set_state(OrderState.waiting_for_external_receipt)
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))
    try:
        if curr == "egp":
            pay_text = (
                f"📲 <b>Direct Payment Details:</b>\n\n"
                f"🇪🇬 <b>Vodafone Cash (Egypt):</b>\n"
                f"• Number: <code>{VODAFONE_NUMBER}</code> ({egp_price:.0f} EGP)\n\n"
                "📸 Please send the <b>transfer screenshot</b> photo now:"
            )
        else:
            pay_text = (
                f"📲 <b>Direct Payment Details:</b>\n\n"
                f"🌐 <b>Binance USDT TRC20 (International):</b>\n"
                f"• Address: <code>{USDT_TRC20_ADDRESS}</code> (${usdt_price:.2f} USDT)\n\n"
                "📸 Please send the <b>transfer screenshot</b> photo now:"
            )
        await callback.message.edit_text(pay_text, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.message(OrderState.waiting_for_external_receipt, F.photo)
async def handle_external_receipt_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(receipt_photo_id=photo_id)
    await state.set_state(OrderState.waiting_for_external_details)
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu"))
    await message.answer(
        "✍️ Receipt image received!\n\n"
        "• Send your <b>TXID / Order ID</b> (for Crypto) OR <b>Phone Number</b> (for Vodafone Cash):",
        reply_markup=builder.as_markup()
    )

@router.message(OrderState.waiting_for_external_receipt)
async def handle_external_receipt_wrong(message: types.Message, state: FSMContext):
    await message.answer("❌ Please send the receipt screenshot photo first.")

@router.message(OrderState.waiting_for_external_details)
async def handle_external_details_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("receipt_photo_id")
    details = message.text.strip() if message.text else "No details"
    user = message.from_user
    prod_title = data.get("product_title", "Product")
    prod_key = data.get("product_key", "item")
    curr = data.get("selected_currency", "egp")
    price = data.get("product_price_egp", 0.0) if curr == "egp" else (data.get("product_price_usdt", 0.0) * USDT_EGP_RATE)
    user_username = f"@{user.username}" if user.username else "N/A"

    order_id = save_active_order(user.id, prod_title, prod_key, user_username, 0, price, payment_type="external", receipt_file_id=photo_id)

    await message.answer("✅ Direct payment order submitted successfully! Waiting for admin review and approval.")

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Accept & Deliver", callback_data=f"accept_{order_id}"),
        types.InlineKeyboardButton(text="❌ Reject Order", callback_data=f"reject_{order_id}")
    )
    builder.row(types.InlineKeyboardButton(text="🚫 Ban User", callback_data=f"ban_user_{user.id}"))

    admin_caption = (
        f"📦 <b>New Direct Payment Order #{order_id}</b>\n\n"
        f"Product: <b>{prod_title}</b>\n"
        f"Price: <b>{price:.2f} EGP</b>\n"
        f"Sender Phone / TXID: <code>{details}</code>\n"
        f"User: <b>{user.full_name}</b> ({user_username} | ID: <code>{user.id}</code>)"
    )
    if photo_id:
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, reply_markup=builder.as_markup())
        except:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_caption, reply_markup=builder.as_markup())
    else:
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_caption, reply_markup=builder.as_markup())
        except:
            pass
    await state.clear()

@router.callback_query(F.data.startswith("accept_"))
async def admin_accept_order(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    order_id = int(callback.data.split("_")[1])
    order_data = get_active_order(order_id)
    if not order_data:
        await safe_answer_callback(callback, "⚠️ Order already processed.", show_alert=True)
        return

    target_user_id, product_title, product_key, _, seller_id, item_price, payment_type, _ = order_data

    auto_code, auto_seller_id, auto_price = get_stock_code(product_key)
    if auto_code:
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE active_orders SET seller_id = ?, item_price = ? WHERE order_id = ?", (auto_seller_id, auto_price if auto_price > 0 else item_price, order_id))
        conn.commit()
        conn.close()
        
        await deliver_order(order_id, auto_code, callback.message)
    else:
        await state.update_data(current_order_id=order_id)
        await state.set_state(AdminState.waiting_for_code)
        await callback.message.reply(f"⚠️ Stock is empty for order #{order_id}.\nSend code manually in message now:")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_code)
async def admin_send_code_manual(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    order_id = data.get("current_order_id")
    
    if not order_id:
        pending = get_all_pending_orders()
        if pending:
            order_id = pending[-1][0]

    if order_id:
        game_code = message.text.strip() if message.text else ""
        if not game_code:
            await message.reply("❌ Please send valid text code.")
            return
        await deliver_order(order_id, game_code, message)
        await state.clear()

async def deliver_order(order_id, game_code, message_obj):
    order_data = get_active_order(order_id)
    if not order_data: return

    target_user_id, product_name, product_key, user_username, seller_id, item_price, payment_type, _ = order_data

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, username FROM users WHERE user_id = ?", (target_user_id,))
    b_row = cursor.fetchone()
    conn.close()
    
    b_name = b_row[0] if b_row else "Unknown"
    b_uname = f"@{b_row[1]}" if b_row and b_row[1] else "No Username"

    seller_info_str = "Admin Direct Stock 👑"
    net_profit = 0.0
    if seller_id > 0 and item_price > 0:
        sales_cnt = get_seller_data(seller_id)[2]
        fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
        store_commission = item_price * fee_rate
        net_profit = item_price - store_commission
        
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET seller_pending_balance = seller_pending_balance + ?, seller_sales_count = seller_sales_count + 1 WHERE user_id = ?", (net_profit, seller_id))
        conn.commit()
        conn.close()

        s_bal, pending_bal, s_sales, _, s_name, s_uname = get_seller_data(seller_id)
        s_username_str = f"@{s_uname}" if s_uname and s_uname != "N/A" else "No Username"
        seller_info_str = f"<b>{s_name}</b> ({s_username_str} | ID: <code>{seller_id}</code>)"

        try:
            await bot.send_message(
                chat_id=seller_id, 
                text=f"🎉 <b>One of your stock items was sold!</b>\n\n📦 Product: <b>{product_name}</b>\n🔑 Code Sold: <code>{game_code}</code>\n⏳ Net Profit Added to Escrow: <b>{net_profit:.2f} EGP</b>"
            )
        except:
            pass

    trans_id = save_user_purchased_code(target_user_id, product_name, game_code, seller_id, item_price, net_profit)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ تأكيد شحن الكود بنجاح", callback_data=f"confirm_deliv_{trans_id}"))
    builder.row(types.InlineKeyboardButton(text="🔄 Request Refund", callback_data=f"req_refund_{trans_id}"))

    try:
        await bot.send_message(
            chat_id=target_user_id, 
            text=(
                f"✅ Your order has been approved and delivered!\n\n"
                f"📦 Product: <b>{product_name}</b>\n"
                f"🔑 Code: <code>{game_code}</code>\n\n"
                f"👇 اضغط على تأكيد الشحن أدناه بعد إتمام التجربة:"
            ), 
            reply_markup=builder.as_markup()
        )
        
        try:
            await bot.send_message(chat_id=DELIVERY_PROOF_CHANNEL_ID, text=f"✅ New order delivered.\nProduct: {product_name}")
        except Exception as e:
            logging.error(f"Failed to send to delivery proof channel: {e}")

        admin_sale_notice = (
            f"🛍️ <b>Order #{order_id} Delivered Successfully!</b>\n\n"
            f"👤 <b>Buyer Details:</b>\n"
            f"• Name: <b>{b_name}</b>\n"
            f"• Username: <b>{b_uname}</b>\n"
            f"• ID: <code>{target_user_id}</code>\n\n"
            f"📦 <b>Order Info:</b>\n"
            f"• Product: <b>{product_name}</b>\n"
            f"• Code: <code>{game_code}</code>\n"
            f"• Price: <b>{item_price:.2f} EGP</b>\n\n"
            f"🏷️ <b>Seller Source:</b> {seller_info_str}"
        )
        
        await bot.send_message(chat_id=ADMIN_ID, text=admin_sale_notice)

        delete_active_order(order_id)
        if isinstance(message_obj, types.Message):
            await message_obj.reply(f"✅ Code delivered for order #{order_id}.")
    except Exception as e:
        if isinstance(message_obj, types.Message):
            await message_obj.reply(f"❌ Error sending code: {e}")

@router.callback_query(F.data.startswith("rate_"))
async def process_user_rating(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    trans_id = int(parts[1])
    stars = int(parts[2])
    user = callback.from_user

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE purchased_transactions SET rating = ? WHERE id = ? AND user_id = ?", (stars, trans_id, user.id))
    cursor.execute("SELECT product_name FROM purchased_transactions WHERE id = ?", (trans_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()

    stars_str = "⭐" * stars

    await safe_answer_callback(callback, f"Thank you for rating us {stars_str}!", show_alert=True)
    try:
        await callback.message.edit_text(callback.message.text + f"\n\n⭐ <b>Your Rating:</b> {stars_str}\nThank you!")
    except:
        pass

@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_order(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    order_id = int(callback.data.split("_")[1])
    
    await state.update_data(reject_order_id=order_id)
    await state.set_state(AdminState.waiting_for_reject_reason)
    
    await callback.message.reply("✍️ أرسل سبب الرفض الآن في رسالة (سيتم إرسالها للعميل مع يوزر الدعم تلقائياً):")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_reject_reason)
async def admin_send_reject_reason(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    order_id = data.get("reject_order_id")
    
    custom_reason = message.text.strip() if message.text else "تم تكرار العملية الإيصال مستخدم مسبقاً"
    
    order_data = get_active_order(order_id)
    if order_data:
        target_user_id, product_title, _, _, _, item_price, payment_type, _ = order_data
        
        if payment_type == "wallet":
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (item_price, target_user_id))
            conn.commit()
            conn.close()

        try:
            msg_to_user = (
                f"❌ عذراً، تم رفض طلبك للباقة (<b>{product_title}</b>).\n"
                f"📌 <b>السبب:</b> {custom_reason}\n\n"
                f"💬 لمعرفة التفاصيل أو لأي استفسار، تواصل مع الدعم الفني: @{SUPPORT_USERNAME}"
            )
            
            await bot.send_message(chat_id=target_user_id, text=msg_to_user)
            delete_active_order(order_id)
            await message.reply("✅ تم رفض الطلب وإرسال السبب للعميل بنجاح.")
        except Exception as e:
            await message.reply(f"❌ خطأ أثناء إرسال الرسالة للعميل: {e}")
            
    await state.clear()

@router.callback_query(F.data.startswith("req_refund_"))
async def process_inline_refund_request(callback: types.CallbackQuery):
    trans_id = int(callback.data.split("_")[2])
    user = callback.from_user

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, price, purchase_time, is_refunded, user_id, product_name, game_code FROM purchased_transactions WHERE id = ?", (trans_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[3] == 1 or row[4] != user.id:
        await safe_answer_callback(callback, "⚠️ Invalid request or already refunded.", show_alert=True)
        return

    seller_id, price, _, _, _, product_name, game_code = row
    await safe_answer_callback(callback, "⏳ Refund request submitted to Admin.", show_alert=True)

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Approve Refund", callback_data=f"adm_app_ref_{trans_id}"),
        types.InlineKeyboardButton(text="❌ Reject Refund", callback_data=f"adm_rej_ref_{trans_id}")
    )

    admin_msg = (
        f"🔄 <b>New Refund Request #{trans_id}</b>\n\n"
        f"👤 Customer: <b>{user.full_name}</b> (ID: <code>{user.id}</code>)\n"
        f"📦 Product: <b>{product_name}</b>\n"
        f"🔑 Code: <code>{game_code}</code>\n"
        f"💰 Price: <b>{price:.2f} EGP</b>"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=builder.as_markup())
    except:
        pass

@router.callback_query(F.data.startswith("adm_app_ref_"))
async def admin_approve_refund(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    trans_id = int(callback.data.split("_")[3])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, seller_id, price, net_profit, is_refunded, product_name, game_code, escrow_released FROM purchased_transactions WHERE id = ?", (trans_id,))
    row = cursor.fetchone()

    if not row or row[4] == 1:
        conn.close()
        await safe_answer_callback(callback, "⚠️ Request already processed.", show_alert=True)
        return

    user_id, seller_id, price, net_profit, _, product_name, game_code, released = row
    cursor.execute("UPDATE purchased_transactions SET is_refunded = 1 WHERE id = ?", (trans_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
    
    if seller_id > 0:
        if released == 1:
            cursor.execute("UPDATE users SET seller_balance = seller_balance - ? WHERE user_id = ?", (net_profit, seller_id))
        else:
            cursor.execute("UPDATE users SET seller_pending_balance = seller_pending_balance - ? WHERE user_id = ?", (net_profit, seller_id))

        try:
            await bot.send_message(
                chat_id=seller_id,
                text=f"⚠️ <b>Notice: Refund Processed</b>\n\nProduct: <b>{product_name}</b>\nCode: <code>{game_code}</code>\n\nFunds have been refunded to the customer, and <b>{net_profit:.2f} EGP</b> has been deducted from your balance/escrow."
            )
        except:
            pass

    conn.commit()
    conn.close()

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Refund Approved!</b>\n\nYour refund request for <b>{product_name}</b> has been approved, and <b>{price:.2f} EGP</b> has been added back to your wallet balance."
        )
    except:
        pass

    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Approved & Refunded.")
    except:
        pass
    await safe_answer_callback(callback, "✅ Refund approved successfully.")

@router.callback_query(F.data.startswith("adm_rej_ref_"))
async def admin_reject_refund(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    trans_id = int(callback.data.split("_")[3])
    await state.update_data(reject_refund_trans_id=trans_id)
    await state.set_state(AdminState.waiting_for_refund_reject_reason)
    await callback.message.reply(f"✍️ Enter reject reason for refund #{trans_id}:")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_refund_reject_reason)
async def admin_send_refund_reject_reason(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    trans_id = data.get("reject_refund_trans_id")
    reason = message.text.strip() if message.text else "No reason provided"

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, product_name FROM purchased_transactions WHERE id = ?", (trans_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        target_user_id, product_name = row
        try:
            await bot.send_message(chat_id=target_user_id, text=f"❌ Refund request for ({product_name}) was rejected.\nReason: {reason}")
            await message.reply(f"🚫 Refund request #{trans_id} rejected.")
        except:
            pass
    await state.clear()

@router.callback_query(F.data.startswith("ban_user_"))
async def admin_ban_user_btn(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    target_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'blocked' WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    await safe_answer_callback(callback, "🚫 User banned successfully.", show_alert=True)

@router.callback_query(F.data == "adm_toggle_maintenance")
async def toggle_maintenance_mode(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    global maintenance_mode
    maintenance_mode = not maintenance_mode
    status_str = "Enabled" if maintenance_mode else "Disabled"
    await safe_answer_callback(callback, f"Maintenance: {status_str}", show_alert=True)

@router.callback_query(F.data == "adm_sellers_stock_list")
async def admin_sellers_stock_list_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT u.user_id, u.full_name, u.username 
        FROM users u 
        INNER JOIN stock s ON u.user_id = s.seller_id 
        WHERE s.status = 'active' AND s.seller_id > 0
    """)
    sellers = cursor.fetchall()
    
    if not sellers:
        msg = "ℹ️ No stock uploaded by any seller currently."
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
    else:
        msg = f"🔑 <b>Sellers Stock Overview ({len(sellers)} sellers):</b>\n\n"
        builder = InlineKeyboardBuilder()
        for s_id, s_name, s_uname in sellers:
            cursor.execute("SELECT COUNT(*) FROM stock WHERE seller_id = ? AND status = 'active'", (s_id,))
            total_codes = cursor.fetchone()[0]
            msg += f"👤 <b>{s_name}</b> (ID: <code>{s_id}</code>) - Codes: <b>{total_codes}</b>\n"
            builder.row(types.InlineKeyboardButton(text=f"🔍 Manage Codes ({s_name})", callback_data=f"adm_view_s_codes_{s_id}"))
        builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))

    conn.close()
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_view_s_codes_"))
async def admin_view_specific_seller_codes(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    seller_id = int(callback.data.split("_")[4])
    
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (seller_id,))
    s_row = cursor.fetchone()
    seller_name = s_row[0] if s_row else f"ID {seller_id}"
    
    cursor.execute("SELECT id, product_key, code FROM stock WHERE seller_id = ? AND status = 'active'", (seller_id,))
    codes = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    if not codes:
        msg = f"ℹ️ No active stock found for <b>{seller_name}</b>."
    else:
        msg = f"📋 <b>Codes for {seller_name} ({len(codes)} items):</b>\n\n"
        for st_id, p_key, code_val in codes:
            p_title = PRODUCTS_TITLES.get(p_key, p_key)
            builder.row(types.InlineKeyboardButton(text=f"🗑️ Delete [{p_title} | {code_val}]", callback_data=f"adm_del_st_{st_id}_{seller_id}"))

    builder.row(types.InlineKeyboardButton(text="⬅️ Back", callback_data="adm_sellers_stock_list"))
    try:
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_del_st_"))
async def admin_delete_seller_stock_code(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    st_id = int(parts[3])
    seller_id = int(parts[4])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stock WHERE id = ?", (st_id,))
    conn.commit()
    conn.close()

    await safe_answer_callback(callback, "✅ Code deleted successfully.", show_alert=True)
    callback.data = f"adm_view_s_codes_{seller_id}"
    await admin_view_specific_seller_codes(callback)

@router.callback_query(F.data.in_(["adm_users_balances", "adm_sellers_list", "adm_pending_withdrawals", "adm_manage_balance", "adm_ledger_history", "adm_warning_menu", "adm_users_report", "adm_broadcast", "adm_ban_menu"]))
async def admin_buttons_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    action = callback.data
    
    if action == "adm_users_balances":
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, full_name, balance FROM users ORDER BY balance DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        msg = "👥 Top Users Balances:\n\n"
        for u_id, name, bal in rows:
            msg += f"👤 <b>{name}</b> (ID: <code>{u_id}</code>) - <b>{bal:.2f} EGP</b>\n"
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())

    elif action == "adm_sellers_list":
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, full_name, seller_balance, seller_pending_balance, seller_sales_count FROM users WHERE is_seller = 1")
        sellers = cursor.fetchall()
        conn.close()
        msg = f"⭐ Sellers List ({len(sellers)}):\n"
        builder = InlineKeyboardBuilder()
        for s_id, name, bal, pending_bal, sales in sellers:
            msg += f"\n👤 <b>{name}</b> (ID: <code>{s_id}</code>)\n💰 Available: <b>{bal:.2f} EGP</b> | Pending: <b>{pending_bal:.2f} EGP</b> | Sales: <b>{sales}</b>"
            builder.row(
                types.InlineKeyboardButton(text=f"🗑️ Clear", callback_data=f"adm_zero_sbal_{s_id}"),
                types.InlineKeyboardButton(text=f"➕ Add", callback_data=f"adm_add_sbal_{s_id}")
            )
            builder.row(types.InlineKeyboardButton(text=f"❌ Remove {name}", callback_data=f"adm_demote_seller_{s_id}"))
        builder.row(types.InlineKeyboardButton(text="➕ Promote User", callback_data="adm_prompt_promote_seller"))
        builder.row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())

    elif action == "adm_pending_withdrawals":
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT id, seller_id, amount, details FROM seller_withdrawals WHERE status = 'pending'")
        ws = cursor.fetchall()
        conn.close()
        msg = f"💸 Pending Withdrawals ({len(ws)}):\n\n" if ws else "ℹ️ No pending withdrawals."
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        await callback.message.edit_text(msg, reply_markup=builder.as_markup())

    elif action == "adm_manage_balance":
        await state.set_state(AdminState.waiting_for_balance_change)
        await callback.message.answer("⚙️ Send balance adjustment in format:\n`USER_ID AMOUNT`")

    elif action == "adm_ban_menu":
        await state.set_state(AdminState.waiting_for_ban_user_id)
        await callback.message.answer("🔨 أرسل (آي دي - ID) المستخدم الذي تريد حظره أو إلغاء حظره في رسالة:")

    elif action == "adm_ledger_history":
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        await callback.message.edit_text("📜 Ledger History", reply_markup=builder.as_markup())

    elif action == "adm_warning_menu":
        await state.set_state(AdminState.waiting_for_warning)
        await callback.message.answer("⚠️ Send warning in format:\n`USER_ID MESSAGE`")

    elif action == "adm_users_report":
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        conn.close()
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="👑 Admin Panel", callback_data="admin_panel_btn"))
        await callback.message.answer(f"📊 Total Users: <b>{total}</b>", reply_markup=builder.as_markup())

    elif action == "adm_broadcast":
        await state.set_state(AdminState.waiting_for_broadcast)
        await callback.message.answer("📢 Send message to broadcast:")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_ban_user_id)
async def admin_ban_unban_process(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.text.strip())
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("SELECT status, full_name FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        
        if not res:
            await message.reply("❌ هذا المستخدم غير مسجل في قاعدة البيانات.")
            conn.close()
            await state.clear()
            return
            
        current_status, u_name = res
        new_status = 'active' if current_status == 'blocked' else 'blocked'
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (new_status, target_id))
        conn.commit()
        conn.close()
        
        status_text = "🟢 تم إلغاء الحظر وتفعيل المستخدم بنجاح" if new_status == 'active' else "🔴 تم حظر المستخدم بنجاح"
        await message.reply(f"{status_text}\nالمستخدم: <b>{u_name}</b> (ID: <code>{target_id}</code>)")
    except ValueError:
        await message.reply("❌ يجيب إرسال رقم الـ ID صحيحاً بالأرقام فقط:")
    await state.clear()

@router.callback_query(F.data.startswith("adm_zero_sbal_"))
async def adm_zero_seller_balance(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    seller_id = int(callback.data.split("_")[3])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET seller_balance = 0.0 WHERE user_id = ?", (seller_id,))
    conn.commit()
    conn.close()
    await safe_answer_callback(callback, "✅ Balance cleared.", show_alert=True)

@router.callback_query(F.data.startswith("adm_add_sbal_"))
async def adm_add_seller_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    seller_id = int(callback.data.split("_")[3])
    await state.update_data(target_seller_id=seller_id)
    await state.set_state(AdminState.waiting_for_seller_balance_adjust)
    await callback.message.answer("✍️ Send amount to add to seller balance:")
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_seller_balance_adjust)
async def adm_add_seller_balance_exec(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    seller_id = data.get("target_seller_id")
    try:
        amount = float(message.text.strip())
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET seller_balance = seller_balance + ? WHERE user_id = ?", (amount, seller_id))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Adjusted seller balance by {amount:+.2f} EGP.")
        await state.clear()
    except ValueError:
        await message.reply("❌ Send valid number:")

@router.callback_query(F.data == "adm_prompt_promote_seller")
async def adm_prompt_promote_seller(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminState.waiting_for_seller_toggle)
    await callback.message.answer("Send User ID to promote as Seller:")
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("adm_demote_seller_"))
async def adm_demote_seller(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    target_id = int(callback.data.split("_")[3])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_seller = 0 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    await safe_answer_callback(callback, f"✅ Seller revoked for ID {target_id}", show_alert=True)

@router.message(AdminState.waiting_for_seller_toggle)
async def admin_execute_seller_toggle(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.text.strip())
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_seller = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Promoted User ID {target_id} to Seller.")
    except ValueError:
        await message.reply("❌ Send numbers only:")
    await state.clear()

@router.message(AdminState.waiting_for_balance_change)
async def admin_change_balance_exec(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.strip().split(maxsplit=1)
        target_id = int(parts[0])
        amount = float(parts[1])
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Adjusted balance by {amount} EGP.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

@router.message(AdminState.waiting_for_warning)
async def admin_send_warning_exec(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.strip().split(maxsplit=1)
        target_id = int(parts[0])
        await bot.send_message(chat_id=target_id, text=f"⚠️ Warning: {parts[1]}")
        await message.reply("✅ Warning sent.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    await state.clear()

@router.message(AdminState.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    for (u_id,) in users:
        try:
            await bot.send_message(chat_id=u_id, text=message.text)
            await asyncio.sleep(0.04)
        except:
            pass
    await message.reply("✅ Broadcast completed.")
    await state.clear()

@router.callback_query(F.data == "my_codes_history")
async def show_user_codes(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_name, game_code, date_time, is_refunded FROM purchased_transactions WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    builder = InlineKeyboardBuilder()
    if not rows:
        history_text = "📦 <b>Purchase History:</b>\n\nℹ️ No purchases yet."
    else:
        history_text = f"📦 <b>Purchase History ({len(rows)} items):</b>\n\n"
        for r_id, p_name, g_code, d_time, refunded in rows:
            history_text += f"🔹 <b>{p_name}</b>\n🔑 Code: <code>{g_code}</code>\n📅 Date: <i>{d_time}</i>\n"
            if refunded != 1:
                builder.row(types.InlineKeyboardButton(text=f"🔄 Request Refund ({p_name})", callback_data=f"req_refund_{r_id}"))
            history_text += "--------------------------------\n"

    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    try:
        await callback.message.edit_text(history_text, reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

async def show_faq_msg(message: types.Message):
    faq_text = "❓ <b>FAQ & Support:</b>\nChoose packages, pay via wallet or direct payment, and enjoy instant/secure delivery."
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    await message.answer(faq_text, reply_markup=builder.as_markup())

@router.callback_query(F.data.in_(["faq_menu", "about_store", "my_profile", "main_menu"]))
async def general_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if callback.data == "main_menu":
        balance = get_user_balance(user_id)
        try:
            await callback.message.edit_text(f"Welcome back to <b>Gk Games</b> Store 🎮\nBalance: <b>{balance:.2f} EGP</b>", reply_markup=get_main_keyboard(user_id))
        except:
            pass
    elif callback.data == "my_profile":
        bal = get_user_balance(user_id)
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
        try:
            await callback.message.edit_text(f"👤 Profile:\nID: <code>{user_id}</code>\nBalance: <b>{bal:.2f} EGP</b>", reply_markup=builder.as_markup())
        except:
            pass
    elif callback.data == "faq_menu":
        await show_faq_msg(callback.message)
    elif callback.data == "about_store":
        builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
        try:
            await callback.message.edit_text("ℹ️ <b>Gk Games Store</b>\n\nYour trusted store for gaming top-ups and digital products.", reply_markup=builder.as_markup())
        except:
            pass
    await safe_answer_callback(callback)

async def auto_release_escrow_task():
    while True:
        await asyncio.sleep(60)
        try:
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            cursor = conn.cursor()
            
            one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                SELECT id, seller_id, net_profit FROM purchased_transactions 
                WHERE seller_id > 0 AND escrow_released = 0 AND is_refunded = 0 AND purchase_time <= ?
            """, (one_hour_ago,))
            
            expired_rows = cursor.fetchall()
            for trans_id, seller_id, net_profit in expired_rows:
                cursor.execute("UPDATE purchased_transactions SET escrow_released = 1 WHERE id = ?", (trans_id,))
                cursor.execute("UPDATE users SET seller_pending_balance = seller_pending_balance - ?, seller_balance = seller_balance + ? WHERE user_id = ?", (net_profit, net_profit, seller_id))
                
                try:
                    await bot.send_message(
                        chat_id=seller_id,
                        text=f"🟢 <b>Escrow Released Automatically!</b>\nTransaction #{trans_id} has passed 1 hour without dispute. Net profit of <b>{net_profit:.2f} EGP</b> has been moved to your available balance!"
                    )
                except:
                    pass
                    
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error in auto_release_escrow_task: {e}")

dp.include_router(router)

async def main():
    await set_bot_commands()
    asyncio.create_task(auto_release_escrow_task())
    print("Super Bot Pro Edition running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
