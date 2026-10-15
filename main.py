import asyncio
import logging
import sqlite3
import time
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

# Payment Details
VODAFONE_NUMBER = "01008924340"
USDT_TRC20_ADDRESS = "TZFH6r1gLj94GWMqAQ71p3uixB7HTd9ZVL"

USDT_EGP_RATE = 50.0  
MIN_DEPOSIT_AMOUNT = 200.0  
SELLER_UPGRADE_COST_EGP = 1250.0 
SELLER_MIN_WITHDRAW = 200.0 

DEFAULT_PLATFORM_FEE = 0.02  
VIP_PLATFORM_FEE = 0.01      

# Channels Setup
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

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

DB_NAME = "store_v23.db"
user_last_action = {}
SPAM_DELAY = 1.0  
maintenance_mode = False  
price_increase_hours = 8.0 

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
            seller_sales_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
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
        CREATE TABLE IF NOT EXISTS pending_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            product_key TEXT,
            code TEXT UNIQUE,
            price REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_balance_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            target_user_id INTEGER,
            amount REAL,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_refunded INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
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
        cursor.execute("ALTER TABLE purchased_transactions ADD COLUMN rating INTEGER DEFAULT 0")
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
        cursor.execute("SELECT seller_balance, seller_sales_count, is_seller, full_name, username FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        return res if res else (0.0, 0, 0, "Unknown", "N/A")
    except:
        return (0.0, 0, 0, "Unknown", "N/A")

def is_user_seller(user_id):
    if user_id == ADMIN_ID: return True
    _, _, is_sell, _, _ = get_seller_data(user_id)
    return is_sell == 1

def save_user(user_id, full_name, username):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, status FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(
            "INSERT INTO users (user_id, full_name, username, balance, has_purchased, status) VALUES (?, ?, ?, 0.0, 0, 'active')",
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

def save_user_purchased_code(user_id, product_name, game_code, seller_id=0, price=0.0):
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO user_codes (user_id, product_name, game_code, date_time) VALUES (?, ?, ?, ?)", (user_id, product_name, game_code, current_time))
    cursor.execute("INSERT INTO purchased_transactions (user_id, seller_id, product_name, game_code, price, purchase_time, date_time) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                   (user_id, seller_id, product_name, game_code, price, current_time, current_time))
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
    waiting_for_price_hours = State()

class QuickSearchState(StatesGroup):
    waiting_for_player_id = State()

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
    builder.row(types.InlineKeyboardButton(text="🔍 Quick Search by Player ID", callback_data="quick_search_id"))
    
    builder.row(
        types.InlineKeyboardButton(text="📖 Guides & Updates", url=GUIDE_UPDATES_LINK),
        types.InlineKeyboardButton(text="📦 Live Stock Channel", url=STOCK_ALERT_LINK)
    )
    builder.row(types.InlineKeyboardButton(text="✅ Live Deliveries Channel", url=DELIVERY_PROOF_LINK))
    
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

def get_seller_keyboard():
    builder = InlineKeyboardBuilder()
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
    builder.row(types.InlineKeyboardButton(text="✏️ Edit Product Prices (EGP / USDT)", callback_data="adm_edit_prices_menu"))
    builder.row(types.InlineKeyboardButton(text="⏱️ Set EGP Price Increase Timer", callback_data="adm_set_timer"))
    builder.row(types.InlineKeyboardButton(text="📈 Comprehensive Sales Analytics", callback_data="adm_sales_analytics"))
    builder.row(types.InlineKeyboardButton(text="💎 Net Profit Report", callback_data="adm_net_profits"))
    builder.row(types.InlineKeyboardButton(text="👥 Users Balances", callback_data="adm_users_balances"))
    builder.row(types.InlineKeyboardButton(text="⭐ Sellers List & Control", callback_data="adm_sellers_list"))
    builder.row(types.InlineKeyboardButton(text="🔑 Sellers Stock & Sales", callback_data="adm_sellers_stock_list"))
    builder.row(types.InlineKeyboardButton(text="⏳ Pending Orders", callback_data="adm_pending_orders"))
    builder.row(types.InlineKeyboardButton(text="💸 Pending Withdrawals", callback_data="adm_pending_withdrawals"))
    builder.row(types.InlineKeyboardButton(text="⚙️ Add/Deduct Balance", callback_data="adm_manage_balance"))
    builder.row(types.InlineKeyboardButton(text="📜 Admin Ledger History", callback_data="adm_ledger_history"))
    builder.row(types.InlineKeyboardButton(text="⚠️ Send Warning / Ban", callback_data="adm_warning_menu"))
    builder.row(types.InlineKeyboardButton(text="📊 Bot Users Report", callback_data="adm_users_report"))
    builder.row(types.InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast"))
    builder.row(types.InlineKeyboardButton(text=maint_text, callback_data="adm_toggle_maintenance"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return builder.as_markup()

@router.message(Command("seller"))
async def cmd_seller(message: types.Message):
    user_id = message.from_user.id
    if not is_user_seller(user_id):
        await message.answer("⚠️ You are not an authorized seller.")
        return
    seller_bal, sales_cnt, _, _, _ = get_seller_data(user_id)
    msg = f"🛠️ Seller Control Panel:\nTotal Sales: {sales_cnt}\nAvailable Profits: {seller_bal:.2f} EGP"
    await message.answer(msg, reply_markup=get_seller_keyboard())

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
        f"Minimum deposit limit: <b>{MIN_DEPOSIT_AMOUNT:.0f} EGP (~${MIN_DEPOSIT_AMOUNT/USDT_EGP_RATE:.1f} USDT)</b>\n\n"
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

    seller_bal, sales_cnt, _, _, _ = get_seller_data(user_id)
    msg = f"🛠️ Seller Control Panel:\nTotal Sales: {sales_cnt}\nAvailable Profits: {seller_bal:.2f} EGP (~${seller_bal/USDT_EGP_RATE:.2f} USDT)"
    try:
        await callback.message.edit_text(msg, reply_markup=get_seller_keyboard())
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

@router.callback_query(F.data == "adm_set_timer")
async def adm_set_timer_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminState.waiting_for_price_hours)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel_btn"))
    try:
        await callback.message.edit_text(
            f"⏱️ Current timer for EGP price increase: <b>{price_increase_hours} hours</b>\n\n"
            f"✍️ Send the new number of hours (e.g., `6`, `12`, `24`):",
            reply_markup=builder.as_markup()
        )
    except:
        pass
    await safe_answer_callback(callback)

@router.message(AdminState.waiting_for_price_hours)
async def adm_save_timer_hours(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    global price_increase_hours
    try:
        hrs = float(message.text.strip())
        if hrs <= 0:
            await message.answer("❌ Hours must be greater than 0.")
            return
        price_increase_hours = hrs
        await message.reply(f"✅ Timer updated! EGP prices will automatically increase after <b>{price_increase_hours} hours</b> (USDT prices remain fixed).")
        await state.clear()
    except ValueError:
        await message.reply("❌ Invalid format. Please send digits only:")

@router.message(SellerState.waiting_for_seller_stock)
async def process_bulk_stock_items(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    p_key = data.get("stock_product_key")
    is_admin = data.get("stock_is_admin", 0)

    if not message.text:
        await message.answer("❌ Please send valid text containing codes.")
        return

    if not p_key:
        await message.answer("❌ Error: Invalid product selection. Please start again.")
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
    await message.answer(f"✅ Stock Added Successfully!\nProduct: <b>{prod_name}</b>\nAdded: <b>{success_count}</b>\nIgnored Duplicates: <b>{duplicate_count}</b>")
    
    if success_count > 0:
        asyncio.create_task(notify_subscribed_users_new_stock(p_key, success_count))
        if is_admin != 1:
            try:
                await bot.send_message(chat_id=ADMIN_ID, text=f"🔔 Seller (ID: <code>{user_id}</code>) added <b>{success_count}</b> codes directly to stock for <b>{prod_name}</b>.")
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
        query = "SELECT seller_id, price FROM purchased_transactions WHERE is_refunded = 0"
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
        
        for seller_id, price in rows:
            if seller_id == 0:
                direct_admin_profits += price
            else:
                sales_cnt = get_seller_data(seller_id)[1]
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
            s_bal, s_sales, _, s_name, s_uname = get_seller_data(s_id)
            fee_rate = VIP_PLATFORM_FEE if s_sales >= 50 else DEFAULT_PLATFORM_FEE
            store_comm = total_vol * fee_rate
            seller_net = total_vol - store_comm
            msg += (
                f"👤 <b>{s_name}</b> (@{s_uname} | ID: <code>{s_id}</code>)\n"
                f"   - Sales: <b>{count}</b>\n"
                f"   - Volume: <b>{total_vol:.2f} EGP</b>\n"
                f"   - Seller Profit: <b>{seller_net:.2f} EGP</b>\n"
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
    cursor.execute("SELECT product_name, game_code, price, date_time FROM purchased_transactions WHERE seller_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        msg = "📊 <b>Your Sales History:</b>\n\nℹ️ No sales recorded yet."
    else:
        msg = f"📊 <b>Your Sales History ({len(rows)} items):</b>\n\n"
        for p_name, g_code, price, d_time in rows:
            msg += f"📦 Product: <b>{p_name}</b>\n🔑 Code Sold: <code>{g_code}</code>\n💰 Price: <b>{price} EGP</b>\n📅 Date: <i>{d_time}</i>\n--------------------\n"

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
    seller_bal, _, _, _, _ = get_seller_data(user_id)
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💸 Request Profit Withdrawal", callback_data="seller_withdraw_request"))
    builder.row(types.InlineKeyboardButton(text="🛠️ Seller Panel", callback_data="seller_panel_btn"))
    try:
        await callback.message.edit_text(f"💰 Available Net Profits: <b>{seller_bal:.2f} EGP (~${seller_bal/USDT_EGP_RATE:.2f} USDT)</b>\n\n(Minimum withdrawal limit: <b>{SELLER_MIN_WITHDRAW} EGP</b>)", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

@router.callback_query(F.data == "seller_withdraw_request")
async def seller_withdraw_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    seller_bal, _, _, _, _ = get_seller_data(user_id)
    if seller_bal < SELLER_MIN_WITHDRAW:
        await safe_answer_callback(callback, f"⚠️ Profits are less than minimum limit ({SELLER_MIN_WITHDRAW} EGP).", show_alert=True)
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
    seller_bal, _, _, _, _ = get_seller_data(user.id)

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
        types.InlineKeyboardButton(text="✅ Approve Withdrawal", callback_data=f"adm_app_w_{w_id}_{user.id}_{int(withdraw_amount)}"),
        types.InlineKeyboardButton(text="❌ Reject Withdrawal", callback_data=f"adm_rej_w_{w_id}_{user.id}")
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
        await bot.send_message(chat_id=seller_id, text=f"✅ Your withdrawal request of <b>{amount:.2f} EGP</b> has been approved and processed.")
    except:
        pass
    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Approved.")
    except:
        pass
    await safe_answer_callback(callback, "Approved successfully.")

@router.callback_query(F.data.startswith("adm_rej_w_"))
async def admin_reject_withdrawal(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    w_id = int(parts[3])
    seller_id = int(parts[4])

    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM seller_withdrawals WHERE id = ?", (w_id,))
    row = cursor.fetchone()
    if row:
        refund_amt = row[0]
        cursor.execute("UPDATE users SET seller_balance = seller_balance + ? WHERE user_id = ?", (refund_amt, seller_id))
    cursor.execute("UPDATE seller_withdrawals SET status = 'rejected' WHERE id = ?", (w_id,))
    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=seller_id, text="❌ Your withdrawal request was rejected by admin and amount returned to your seller balance.")
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
        f"🔸 Minimum Deposit Limit: <b>{MIN_DEPOSIT_AMOUNT:.0f} EGP (~${MIN_DEPOSIT_AMOUNT/USDT_EGP_RATE:.1f} USDT)</b>\n\n"
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

# ==================== SELECTION MENU ====================

@router.callback_query(F.data.in_(["cat_freefire", "cat_pubg"]))
async def ask_currency_selection(callback: types.CallbackQuery):
    cat_type = callback.data.split("_")[1]
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
    else:
        items = ["pubg60", "pubg325", "pubg660", "pubg1800", "pubg3850", "pubg8100"]

    for p_key in items:
        title = PRODUCTS_TITLES.get(p_key, p_key)
        egp_p, usdt_p = get_product_prices(p_key)
        
        if curr == "egp":
            btn_text = f"🔥 {title} - {egp_p:.0f} EGP" if cat_type == "freefire" else f"🎮 {title} - {egp_p:.0f} EGP"
        else:
            btn_text = f"🔥 {title} - ${usdt_p:.2f} USDT" if cat_type == "freefire" else f"🎮 {title} - ${usdt_p:.2f} USDT"
            
        builder.row(types.InlineKeyboardButton(text=btn_text, callback_data=f"buy_{p_key}_{curr}"))

    builder.row(types.InlineKeyboardButton(text="⬅️ Change Currency", callback_data=f"cat_{cat_type}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    
    try:
        await callback.message.edit_text("📦 <b>Select a Package to Buy:</b>", reply_markup=builder.as_markup())
    except:
        pass
    await safe_answer_callback(callback)

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
    
    # السعر المعتمد للشراء بالرصيد هو المصري (EGP)، والدفع الخارجي يقبل العملة المختارة
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
    price = data.get("product_price_egp", 0.0) # المحفظة تُخصم بالمصري EGP

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

    if auto_seller_id > 0:
        sales_cnt = get_seller_data(auto_seller_id)[1]
        fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
        store_commission = price * fee_rate
        net_profit = price - store_commission
        
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET seller_balance = seller_balance + ?, seller_sales_count = seller_sales_count + 1 WHERE user_id = ?", (net_profit, auto_seller_id))
        conn.commit()
        conn.close()

        try:
            await bot.send_message(
                chat_id=auto_seller_id, 
                text=f"🎉 <b>One of your stock items was sold!</b>\n\n📦 Product: <b>{prod_title}</b>\n🔑 Code Sold: <code>{auto_code}</code>\n💰 Net Profit: <b>{net_profit:.2f} EGP</b>"
            )
        except:
            pass

    trans_id = 0
    try:
        trans_id = save_user_purchased_code(user.id, prod_title, auto_code, auto_seller_id, price)
    except:
        pass

    builder = InlineKeyboardBuilder()
    if trans_id > 0:
        builder.row(types.InlineKeyboardButton(text="🔄 Request Refund", callback_data=f"req_refund_{trans_id}"))
    
    builder.row(
        types.InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{trans_id}_1"),
        types.InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{trans_id}_2"),
        types.InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{trans_id}_3"),
        types.InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{trans_id}_4"),
        types.InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{trans_id}_5")
    )

    try:
        await callback.message.edit_text(
            f"✅ <b>Purchase successful!</b>\n\n"
            f"📦 Product: <b>{prod_title}</b>\n"
            f"🔑 Code: <code>{auto_code}</code>\n\n"
            f"🌟 Please rate our service below:",
            reply_markup=builder.as_markup()
        )
    except:
        pass

    try:
        await bot.send_message(chat_id=DELIVERY_PROOF_CHANNEL_ID, text=f"✅ Instant Wallet Order Delivered.\nProduct: {prod_title}")
        await bot.send_message(chat_id=ADMIN_ID, text=f"🛍️ <b>Instant Wallet Purchase!</b>\nBuyer: {user.full_name} (ID: <code>{user.id}</code>)\nProduct: {prod_title}\nCode: <code>{auto_code}</code>")
    except:
        pass

    await state.clear()
    await safe_answer_callback(callback)

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

    seller_info_str = "Admin Direct Stock"
    if seller_id > 0 and item_price > 0:
        seller_bal, sales_cnt, _, s_name, s_uname = get_seller_data(seller_id)
        fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
        store_commission = item_price * fee_rate
        net_profit = item_price - store_commission
        
        conn = sqlite3.connect(DB_NAME, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET seller_balance = seller_balance + ?, seller_sales_count = seller_sales_count + 1 WHERE user_id = ?", (net_profit, seller_id))
        conn.commit()
        conn.close()

        try:
            await bot.send_message(
                chat_id=seller_id, 
                text=f"🎉 <b>One of your stock items was sold!</b>\n\n📦 Product: <b>{product_name}</b>\n🔑 Code Sold: <code>{game_code}</code>\n💰 Net Profit: <b>{net_profit:.2f} EGP</b>"
            )
        except:
            pass

    trans_id = 0
    try:
        trans_id = save_user_purchased_code(target_user_id, product_name, game_code, seller_id, item_price)
    except:
        pass

    try:
        builder = InlineKeyboardBuilder()
        if trans_id > 0:
            builder.row(types.InlineKeyboardButton(text="🔄 Request Refund", callback_data=f"req_refund_{trans_id}"))
        
        builder.row(
            types.InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_{trans_id}_1"),
            types.InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_{trans_id}_2"),
            types.InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_{trans_id}_3"),
            types.InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_{trans_id}_4"),
            types.InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_{trans_id}_5")
        )
        
        await bot.send_message(
            chat_id=target_user_id, 
            text=(
                f"✅ Your order has been approved and delivered!\n\n"
                f"📦 Product: <b>{product_name}</b>\n"
                f"🔑 Code: <code>{game_code}</code>\n\n"
                f"🌟 Please take a moment to rate our service below:"
            ), 
            reply_markup=builder.as_markup()
        )
        
        delivery_channel_msg = f"✅ New order delivered.\nProduct: {product_name}"
        try:
            await bot.send_message(chat_id=DELIVERY_PROOF_CHANNEL_ID, text=delivery_channel_msg)
        except Exception as e:
            logging.error(f"Failed to send to delivery proof channel: {e}")
        
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

    p_name = row[0] if row else "Product"
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
            await bot.send_message(chat_id=target_user_id, text=f"❌ Your order for ({product_title}) was rejected by admin." + (f" Refunded {item_price} EGP to balance." if payment_type=="wallet" else ""))
            delete_active_order(order_id)
            await callback.message.edit_text(callback.message.text + "\n\n❌ Rejected.")
        except:
            pass
    await safe_answer_callback(callback, "Rejected.")

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
    cursor.execute("SELECT user_id, seller_id, price, is_refunded, product_name, game_code FROM purchased_transactions WHERE id = ?", (trans_id,))
    row = cursor.fetchone()

    if not row or row[3] == 1:
        conn.close()
        await safe_answer_callback(callback, "⚠️ Request already processed.", show_alert=True)
        return

    user_id, seller_id, price, _, product_name, game_code = row
    cursor.execute("UPDATE purchased_transactions SET is_refunded = 1 WHERE id = ?", (trans_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price, user_id))
    
    if seller_id > 0:
        sales_cnt = get_seller_data(seller_id)[1]
        fee_rate = VIP_PLATFORM_FEE if sales_cnt >= 50 else DEFAULT_PLATFORM_FEE
        net_seller_deduct = price - (price * fee_rate)
        cursor.execute("UPDATE users SET seller_balance = seller_balance - ? WHERE user_id = ?", (net_seller_deduct, seller_id))

    conn.commit()
    conn.close()

    try:
        await bot.send_message(chat_id=user_id, text=f"✅ <b>Refund approved by admin!</b>\nAdded <b>{price:.2f} EGP</b> back to your balance.")
    except:
        pass

    try:
        await callback.message.edit_text(callback.message.text + "\n\n✅ Approved.")
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

@router.callback_query(F.data.in_(["adm_users_balances", "adm_sellers_list", "adm_pending_withdrawals", "adm_manage_balance", "adm_ledger_history", "adm_warning_menu", "adm_users_report", "adm_broadcast"]))
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
        cursor.execute("SELECT user_id, full_name, seller_balance, seller_sales_count FROM users WHERE is_seller = 1")
        sellers = cursor.fetchall()
        conn.close()
        msg = f"⭐ Sellers List ({len(sellers)}):\n"
        builder = InlineKeyboardBuilder()
        for s_id, name, bal, sales in sellers:
            msg += f"\n👤 <b>{name}</b> (ID: <code>{s_id}</code>)\n💰 Profits: <b>{bal:.2f} EGP</b> | Sales: <b>{sales}</b>"
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
    await safe_answer_callback(callback)

# مهمة خلفية لزيادة أسعار الجنيه المصري (EGP) فقط تلقائياً بعد الساعات المحددة، مع ترك الدولار (USDT) ثابتاً
async def scheduled_price_increase():
    while True:
        global price_increase_hours
        await asyncio.sleep(price_increase_hours * 3600)
        try:
            conn = sqlite3.connect(DB_NAME, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("SELECT product_key, price_egp FROM product_prices")
            rows = cursor.fetchall()
            
            for p_key, current_egp in rows:
                new_egp = current_egp + 3.0  # زيادة 2 جنيه مصري ثابتة على كل منتج (ويمكنك تغييرها لو أردت)
                cursor.execute("UPDATE product_prices SET price_egp = ? WHERE product_key = ?", (new_egp, p_key))
                
            conn.commit()
            conn.close()
            
            await bot.send_message(chat_id=ADMIN_ID, text=f"⏰ <b>Auto-Price Alert:</b> EGP prices have automatically increased by +3 EGP after {price_increase_hours} hours (USDT prices remained unchanged)!")
        except Exception as e:
            logging.error(f"Error in EGP price increase: {e}")

dp.include_router(router)

async def main():
    await set_bot_commands()
    asyncio.create_task(scheduled_price_increase())
    print("Super Bot v25.0 Pro Edition with Separate EGP/USDT Prices is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
