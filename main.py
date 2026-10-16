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
VIP_PLATFORM_FEE = 0.015

LOG_CHANNEL_ID = -1004393845755      
GUIDE_UPDATES_CHANNEL_ID = -1003836643803
STOCK_ALERT_CHANNEL_ID = -1004486768828

GUIDE_UPDATES_LINK = "https://t.me/+r3C8qot_U7ExZTU0"
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

# ==================== STATES ====================
class IDTicketState(StatesGroup):
    waiting_for_player_id = State()
    waiting_for_quantity = State()
    waiting_for_receipt = State()

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

# ==================== ID TICKET SYSTEM ====================

@router.callback_query(F.data == "start_id_ticket")
async def start_id_ticket_process(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(IDTicketState.waiting_for_player_id)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data="main_menu"))
    try:
        await callback.message.edit_text(
            "🎫 <b>فتح تيكيت شحن عن طريق الـ ID Direct:</b>\n\n"
            "الرجاء كتابة **الـ Player ID (الأيدي)** الخاص بك فقط واضغط إرسال:",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.message(IDTicketState.waiting_for_player_id)
async def process_ticket_player_id(message: types.Message, state: FSMContext):
    player_id = message.text.strip() if message.text else ""
    if not player_id:
        await message.answer("❌ يرجى إرسال الـ ID الصحيح فقط:")
        return

    await state.update_data(ticket_player_id=player_id)
    await state.set_state(IDTicketState.waiting_for_quantity)
    
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data="main_menu"))
    await message.answer(
        f"✅ تم تسجيل الـ ID: <code>{player_id}</code>\n\n"
        "الآن يرجى إرسال **الكمية / الباقة المطلوبة** فقط (مثال: `110 جواهر` أو `325 شدة`):",
        reply_markup=builder.as_markup()
    )

@router.message(IDTicketState.waiting_for_quantity)
async def process_ticket_quantity(message: types.Message, state: FSMContext):
    quantity = message.text.strip() if message.text else ""
    if not quantity:
        await message.answer("❌ يرجى كتابة الكمية المطلوبة فقط:")
        return

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

    try:
        sent_msg = await bot.send_message(chat_id=ADMIN_ID, text=admin_notice, reply_markup=builder.as_markup())
        await state.update_data(admin_notice_id=sent_msg.message_id)
        await message.answer(
            "✅ <b>تم فتح التيكيت وإرساله للدعم بنجاح!</b>\n\n"
            "سيصلك إشعار بالسعر وطريقة الدفع فوراً."
        )
    except Exception as e:
        await message.answer("❌ حدث خطأ أثناء إرسال التيكيت، حاول مجدداً.")

    await state.clear()

@router.callback_query(F.data.startswith("set_price_t_"))
async def admin_start_set_ticket_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    target_user_id = int(callback.data.split("_")[3])
    await state.update_data(target_ticket_user=target_user_id)
    await state.set_state(AdminSetPriceState.waiting_for_price)
    await callback.message.reply("✍️ **أدخل السعر المطلوب من العميل بالجنيه (EGP) بالأرقام فقط:**")
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
            types.InlineKeyboardButton(text="🌐 USDT (TRC20)", callback_data=f"send_pay_usdt_{target_user_id}_{usdt_price}")
        )

        await message.answer(
            f"💰 السعر المكتوب: <b>{price:.2f} EGP</b> (~${usdt_price:.2f} USDT)\nاختر طريقة الدفع التي ستبعتها للعميل:",
            reply_markup=builder.as_markup()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ يرجى كتابة السعر بالأرقام فقط:")

@router.callback_query(F.data.startswith("send_pay_"))
async def send_payment_details_to_user(callback: types.CallbackQuery, state: FSMContext):
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
            f"📸 بعد التحويل، قم بإرسال صورة الإيصال هنا مباشرة لتأكيد الطلب."
        )
    else:
        pay_msg = (
            f"💳 <b>تسعيرة طلب الشحن الخاص بك:</b>\n\n"
            f"💰 المبلغ المطلوب: <b>${amount:.2f} USDT</b>\n"
            f"🌐 عنوان المحفظة TRC20: <code>{USDT_TRC20_ADDRESS}</code>\n\n"
            f"📸 بعد التحويل، قم بإرسال صورة الإيصال هنا مباشرة لتأكيد الطلب."
        )

    try:
        await bot.send_message(chat_id=target_user_id, text=pay_msg)
        await state.set_state(IDTicketState.waiting_for_receipt)
        await state.update_data(ticket_user_id=target_user_id, ticket_amount=amount)
        await callback.message.edit_text(callback.message.text + "\n\n✅ تم إرسال بيانات الدفع والسعر للعميل بنجاح.")
    except Exception as e:
        await callback.message.reply(f"❌ تعذر الإرسال للعميل: {e}")
    await safe_answer_callback(callback)

@router.message(IDTicketState.waiting_for_receipt, F.photo)
async def process_ticket_receipt_photo(message: types.Message, state: FSMContext):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    
    admin_notice = (
        f"📸 <b>إيصال دفع تيكيت جديد من العميل!</b>\n\n"
        f"👤 <b>العميل:</b> {user.full_name} (@{user.username if user.username else 'لا يوجد'})\n"
        f"🆔 <b>آي دي العميل:</b> <code>{user.id}</code>\n\n"
        f"يرجى مراجعة الإيصال وتأكيد الشحن للعميل."
    )

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ تم الشحن وإغلاق التيكيت", callback_data=f"close_ticket_{user.id}"))

    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_notice, reply_markup=builder.as_markup())
        await message.answer("✅ <b>تم إرسال الإيصال للآدمن بنجاح!</b>\nسيتم مراجعة الدفع وشحن حسابك فوراً.")
    except Exception as e:
        await message.answer(f"❌ حدث خطأ أثناء إرسال الإيصال: {e}")
    await state.clear()

@router.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket_by_admin(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    target_user_id = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="✅ <b>تم شحن طلبك بنجاح وإغلاق التيكيت! نتمنى لك تجربة ممتعة 🎮</b>"
        )
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>تم إغلاق التيكيت وتأكيد الشحن للعميل.</b>")
    except:
        pass
    await safe_answer_callback(callback, "تم الإغلاق بنجاح.")

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

# ==================== WHEEL OF FORTUNE ====================

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

# ==================== SELECTION MENU ====================

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

# ==================== OTHER PANELS ====================

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
    builder.row(types.InlineKeyboardButton(text="✏️ Edit Product Prices", callback_data="adm_edit_prices_menu"))
    builder.row(types.InlineKeyboardButton(text="📈 Comprehensive Sales Analytics", callback_data="adm_sales_analytics"))
    builder.row(types.InlineKeyboardButton(text="💎 Net Profit Report", callback_data="adm_net_profits"))
    builder.row(types.InlineKeyboardButton(text="👥 Users Balances", callback_data="adm_users_balances"))
    builder.row(types.InlineKeyboardButton(text="⭐ Sellers List & Control", callback_data="adm_sellers_list"))
    builder.row(types.InlineKeyboardButton(text="⏳ Pending Orders", callback_data="adm_pending_orders"))
    builder.row(types.InlineKeyboardButton(text="💸 Pending Withdrawals", callback_data="adm_pending_withdrawals"))
    builder.row(types.InlineKeyboardButton(text="⚙️ Add/Deduct Balance", callback_data="adm_manage_balance"))
    builder.row(types.InlineKeyboardButton(text="🔨 Ban / Unban Users Menu", callback_data="adm_ban_menu"))
    builder.row(types.InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"))
    builder.row(types.InlineKeyboardButton(text=maint_text, callback_data="adm_toggle_maintenance"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()

# ==================== BASIC COMMANDS ====================

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

# ==================== SELLER & STOCK MANAGEMENT ====================

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

    price_egp, _ = get_product_prices(p_key)

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()

    for line in lines:
        code = line.strip()
        if not code:
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
    reply_msg += f"• أكواد مكررة تم تجاهلها: <b>{duplicate_count}</b>"

    await message.answer(reply_msg)
    
    if success_count > 0:
        asyncio.create_task(notify_subscribed_users_new_stock(p_key, success_count))
                
    await state.clear()

# ==================== ORDER FLOW & PURCHASES ====================

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

    net_profit = 0.0
    trans_id = save_user_purchased_code(user.id, prod_title, auto_code, auto_seller_id, price, net_profit)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ تأكيد شحن الكود بنجاح", callback_data=f"confirm_deliv_{trans_id}"))

    try:
        await callback.message.edit_text(
            f"✅ <b>Purchase successful!</b>\n\n"
            f"📦 Product: <b>{prod_title}</b>\n"
            f"🔑 Code: <code>{auto_code}</code>\n\n"
            f"👇 اضغط على الزر أدناه لتأكيد شحن الكود:",
            reply_markup=builder.as_markup()
        )
    except:
        pass

    await state.clear()
    await safe_answer_callback(callback)

@router.callback_query(F.data.startswith("confirm_deliv_"))
async def process_confirm_delivery(callback: types.CallbackQuery):
    trans_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE purchased_transactions SET confirmed_delivery = 1 WHERE id = ?", (trans_id,))
    conn.commit()
    conn.close()

    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>تم تأكيد شحن الكود بنجاح! شكراً لتعاملكم معنا 🎮</b>"
        )
    except:
        pass
    await safe_answer_callback(callback, "✅ شكراً لك! تم تأكيد الشحن.", show_alert=True)

# ==================== GENERAL MENU HANDLERS ====================

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
            await callback.message.edit_text(f"ℹ️ <b>Gk Games Store</b>\n\nYour trusted store for gaming top-ups and digital products.", reply_markup=builder.as_markup())
        except:
            pass
    await safe_answer_callback(callback)

async def show_faq_msg(message: types.Message):
    faq_text = "❓ <b>FAQ & Support:</b>\nChoose packages, pay via wallet or direct payment, and enjoy instant/secure delivery."
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    await message.answer(faq_text, reply_markup=builder.as_markup())

dp.include_router(router)

async def main():
    await set_bot_commands()
    print("Super Bot Pro Edition running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
