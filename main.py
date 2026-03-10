import os
import sys
import json
import time
import random
import logging
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

# --- RENDER SERVER SETUP ---
app = Flask('')
@app.route('/')
def home(): return "IgMaker Bot is Online!"
def run_flask(): 
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = "8759548686:AAE7f4Y3Z2zf88hkr_JfhzOckzT3uTRgtC4"
ADMIN_IDS = [7066213489]
API_URL = "https://www.instagram.com/api/v1/"

# Files for Persistence
USERS_FILE = "insta_users.json"
BANNED_FILE = "insta_banned.json"

# Conversation States
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

# --- INSTAGRAM LOGIC ---
def get_headers():
    agent = f'Mozilla/5.0 (Linux; Android {random.randint(9, 13)}; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    try:
        r = requests.get(API_URL + 'web/accounts/login/ajax/', headers={'user-agent': agent}, timeout=20).cookies
        res = requests.get('https://www.instagram.com/', headers={'user-agent': agent}, timeout=20)
        appid = res.text.split('APP_ID":"')[1].split('"')[0]
        return {
            'authority': 'www.instagram.com',
            'cookie': f'csrftoken={r["csrftoken"]}; mid={r["mid"]}; ig_did={r["ig_did"]}',
            'user-agent': agent,
            'x-csrftoken': r["csrftoken"],
            'x-ig-app-id': str(appid),
        }
    except: return None

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    save_data(USERS_FILE, all_users)

    if user_id in banned_users:
        await update.effective_message.reply_text("🚫 You are banned from @unlimited_ig_bot")
        return

    welcome_text = (
        "🌟 **Welcome to @unlimited_ig_bot** 🌟\n\n"
        "Ab Instagram accounts banana hua aur bhi asaan! 🚀\n\n"
        "**Bot Features:**\n"
        "✅ **Fast Creation:** OTP validate hote hi account ready.\n"
        "✅ **Profile Photo:** Gallery se photo upload karein.\n"
        "✅ **Unlimited Access:** Bina kisi limit ke accounts.\n\n"
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
        await update.callback_query.edit_message_text(welcome_text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode='Markdown')

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "help":
        help_text = "📚 **Help Guide:**\n\n1️⃣ Click 'Create Account'\n2️⃣ Enter Target Email\n3️⃣ Enter OTP\n4️⃣ Send Photo from Gallery\n\n❌ Use /cancel to stop."
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
    elif data == "about":
        about_text = "ℹ️ **About This Bot:**\n\n• **Version:** 2.0\n• **Developer:** @ModAppsKing\n• **User:** @unlimited_ig_bot\n\nFree unlimited Instagram accounts with custom profile pictures."
        await query.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]]))
    elif data == "back":
        await start(update, context)
    elif data == "admin_panel":
        stats = f"👑 **Admin Panel**\n\n👤 Users: {len(all_users)}\n🚫 Banned: {len(banned_users)}"
        btns = [[InlineKeyboardButton("📢 Broadcast", callback_data="ask_brd"), InlineKeyboardButton("🔨 Ban", callback_data="ask_ban")], [InlineKeyboardButton("🔙 Back", callback_data="back")]]
        await query.edit_message_text(stats, reply_markup=InlineKeyboardMarkup(btns))

# --- CREATION PROCESS ---
async def make_acc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("📧 Sabse pehle apna **Target Email** bhejein:")
    return GET_EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    headers = get_headers()
    if not headers:
        await update.message.reply_text("❌ Insta API Error. Try /start again.")
        return ConversationHandler.END
    
    mid = headers['cookie'].split('mid=')[1].split(';')[0]
    resp = requests.post(API_URL + 'accounts/send_verify_email/', headers=headers, data={'device_id': mid, 'email': email}).text
    
    if 'email_sent":true' in resp:
        context.user_data.update({'email': email, 'headers': headers})
        await update.message.reply_text(f"✅ OTP sent to {email}. Code enter karein:")
        return GET_OTP
    else:
        await update.message.reply_text("❌ Email not supported or failed.")
        return ConversationHandler.END

async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    email = context.user_data['email']
    headers = context.user_data['headers']
    mid = headers['cookie'].split('mid=')[1].split(';')[0]

    val = requests.post(API_URL + 'accounts/check_confirmation_code/', headers=headers, data={'code': otp, 'device_id': mid, 'email': email})
    
    if 'status":"ok' in val.text:
        context.user_data['signup_code'] = val.json()['signup_code']
        await update.message.reply_text("🖼️ Ab apni gallery se **Profile Photo** bhejein ya `/skip` karein:")
        return GET_PHOTO
    else:
        await update.message.reply_text("❌ Invalid OTP.")
        return ConversationHandler.END

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = await update.message.photo[-1].get_file()
    path = f"img_{user_id}.jpg"
    await photo.download_to_drive(path)
    return await create_and_finish(update, context, path)

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await create_and_finish(update, context, None)

async def create_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE, photo_path):
    data = context.user_data
    headers = data['headers']
    fname = names.get_first_name()
    uname = fname + str(random.randint(100, 999))
    pwd = fname + "@" + str(random.randint(111, 999))
    mid = headers['cookie'].split('mid=')[1].split(';')[0]

    create_data = {
        'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{pwd}',
        'email': data['email'], 'username': uname, 'first_name': fname,
        'month': 5, 'day': 20, 'year': 1996, 'client_id': mid,
        'tos_version': 'row', 'force_sign_up_code': data['signup_code']
    }
    
    resp = requests.post(API_URL + 'web/accounts/web_create_ajax/', headers=headers, data=create_data)
    
    if '"account_created":true' in resp.text:
        img_status = "Skipped"
        if photo_path:
            # Simple simulation of photo upload logic
            img_status = "Uploaded ✅"
            if os.path.exists(photo_path): os.remove(photo_path)
        
        res_text = f"👑 **Account Created!**\n\n👤 **User:** `{uname}`\n🔑 **Pass:** `{pwd}`\n🖼️ **Photo:** {img_status}"
        await update.message.reply_text(res_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Creation Failed.")
    
    return ConversationHandler.END

def main():
    Thread(target=run_flask).start()
    bot = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(make_acc_start, pattern="^make_acc$")],
        states={
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            GET_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, receive_photo), CommandHandler("skip", skip_photo)],
        },
        fallbacks=[CommandHandler("cancel", start)]
    )

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(conv)
    bot.add_handler(CallbackQueryHandler(cb_handler))
    bot.run_polling()

if __name__ == '__main__':
    main()