import os
import json
import time
import random
import requests
import names
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ConversationHandler, 
    filters, 
    ContextTypes
)

# --- RENDER SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Ig Bot with Admin Panel is Online!"
def run_flask(): 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- CONFIG ---
BOT_TOKEN = "8759548686:AAE7f4Y3Z2zf88hkr_JfhzOckzT3uTRgtC4"
ADMIN_IDS = [7066213489]
API_URL = "https://www.instagram.com/api/v1/"

# Persistent Files
USERS_FILE = "insta_users.json"
BANNED_FILE = "insta_banned.json"

# States
GET_EMAIL, GET_OTP, GET_PHOTO = range(3)
BROADCAST_MSG, BAN_ID = range(3, 5)

# --- DATA HELPERS ---
def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f: return set(json.load(f))
        except: return set()
    return set()

def save_data(file, data):
    with open(file, 'w') as f: json.dump(list(data), f)

all_users = load_data(USERS_FILE)
banned_users = load_data(BANNED_FILE)

# --- INSTA HEADERS ---
def get_headers():
    agent = f'Mozilla/5.0 (Linux; Android {random.randint(9, 13)})'
    try:
        r = requests.get(API_URL + 'web/accounts/login/ajax/', headers={'user-agent': agent}, timeout=15).cookies
        res = requests.get('https://www.instagram.com/', headers={'user-agent': agent}, timeout=15)
        appid = res.text.split('APP_ID":"')[1].split('"')[0]
        return {
            'authority': 'www.instagram.com',
            'cookie': f'csrftoken={r["csrftoken"]}; mid={r["mid"]}; ig_did={r["ig_did"]}',
            'user-agent': agent,
            'x-csrftoken': r["csrftoken"],
            'x-ig-app-id': str(appid),
        }
    except: return None

# --- MAIN HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    save_data(USERS_FILE, all_users)

    if user_id in banned_users:
        await update.effective_message.reply_text("🚫 You are banned from @unlimited_ig_bot")
        return

    text = (
        "🌟 **Welcome to @unlimited_ig_bot** 🌟\n\n"
        "Ab Instagram accounts banana hua aur bhi asaan! 🚀\n\n"
        "**Bot Features:**\n"
        "✅ Fast Creation & OTP Support\n"
        "✅ Custom Profile Photo Upload\n"
        "✅ Unlimited Accounts Access\n\n"
        "👇 **Account banana shuru karein:**"
    )
    buttons = [
        [InlineKeyboardButton("🚀 Create Account", callback_data="make_acc")],
        [InlineKeyboardButton("📚 Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    
    markup = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data == "go_start":
        await start(update, context)
    elif data == "help":
        await query.edit_message_text("📚 **Help:**\n\n1. Click Create Account\n2. Enter Email & OTP\n3. Upload Photo\n\n❌ Use /cancel to stop.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_start")]]))
    elif data == "about":
        await query.edit_message_text("ℹ️ **About:**\nUnlimited IG Maker v2.0\nDev: @ModAppsKing", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_start")]]))
    
    # Admin Logic
    if user_id in ADMIN_IDS:
        if data == "admin_panel":
            stats = f"👑 **Admin Panel**\n\n👤 Users: {len(all_users)}\n🚫 Banned: {len(banned_users)}"
            btns = [[InlineKeyboardButton("📢 Broadcast", callback_data="ask_brd"), InlineKeyboardButton("🔨 Ban", callback_data="ask_ban")], [InlineKeyboardButton("🔙 Back", callback_data="go_start")]]
            await query.edit_message_text(stats, reply_markup=InlineKeyboardMarkup(btns))
        elif data == "ask_brd":
            await query.edit_message_text("📢 Send the message to broadcast:")
            return BROADCAST_MSG
        elif data == "ask_ban":
            await query.edit_message_text("🔨 Send the User ID to Ban:")
            return BAN_ID

# --- CREATION & ADMIN ACTIONS ---
async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    headers = get_headers()
    if not headers:
        await update.message.reply_text("❌ Connection Error.")
        return ConversationHandler.END
    
    mid = headers['cookie'].split('mid=')[1].split(';')[0]
    resp = requests.post(API_URL + 'accounts/send_verify_email/', headers=headers, data={'device_id': mid, 'email': email}).json()
    
    if resp.get('email_sent'):
        context.user_data.update({'email': email, 'headers': headers})
        await update.message.reply_text(f"✅ OTP sent to {email}. Code enter karein:")
        return GET_OTP
    await update.message.reply_text("❌ Failed. Try another email.")
    return ConversationHandler.END

async def do_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    for u in all_users:
        try: await context.bot.send_message(u, f"📢 **Broadcast**\n\n{msg}")
        except: pass
    await update.message.reply_text("✅ Sent!")
    return ConversationHandler.END

async def do_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = int(update.message.text)
    banned_users.add(uid)
    save_data(BANNED_FILE, banned_users)
    await update.message.reply_text(f"✅ User {uid} Banned.")
    return ConversationHandler.END

def main():
    Thread(target=run_flask).start()
    bot_app = Application.builder().token(BOT_TOKEN).build()

    # Master Conversation
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_router, pattern="^make_acc$"),
            CallbackQueryHandler(button_router, pattern="^ask_")
        ],
        states={
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_broadcast)],
            BAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_ban)],
        },
        fallbacks=[CommandHandler("cancel", start)]
    )

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(conv)
    bot_app.add_handler(CallbackQueryHandler(button_router))
    
    print("🟢 Bot is Live with Admin Panel!")
    bot_app.run_polling()

if __name__ == '__main__':
    main()
                                      
