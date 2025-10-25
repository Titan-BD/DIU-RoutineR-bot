import json
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# আপনার BotFather থেকে পাওয়া টোকেনটি এখানে পেস্ট করুন
BOT_TOKEN = "8380820208:AAGOGG7QxuFNdr_rosTN38_7dGK1Qb81_xQ" 

# রুটিন ফাইলটি লোড করা
def load_routine():
    with open('routine.json', 'r') as f:
        return json.load(f)

# রুটিন ফরম্যাট করার ফাংশন
def format_schedule(schedule, day_name):
    if not schedule:
        return f"আগামীকাল ({day_name}) কোনো ক্লাস নেই।"

    message = f"📅 **{day_name}**-এর ক্লাসের রুটিন:\n\n"
    for item in schedule:
        message += f"🕑 **সময়:** {item['time']}\n"
        message += f"📚 **কোর্স:** {item['course']}\n"
        message += f"🚪 **রুম:** {item['room']}\n"
        message += "---------------------\n"
    
    return message

# /start কমান্ডের ফাংশন
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"স্বাগতম, {user.first_name}!\n\n"
        f"আমি Daffodil EEE ডিপার্টমেন্টের রুটিন বট।\n\n"
        f"আজকের রুটিন দেখতে টাইপ করুন: /today\n"
        f"আগামীকালের রুটিন দেখতে টাইপ করুন: /tomorrow"
    )

# /today কমান্ডের ফাংশন
async def today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routine = load_routine()
    
    # আজকের দিনের নাম (যেমন: Saturday) বের করা
    # টাইমজোন ঠিক রাখার জন্য (বাংলাদেশ)
    tz = datetime.timezone(datetime.timedelta(hours=6))
    today = datetime.datetime.now(tz).strftime('%A') # %A দিলে দিনের পুরো নাম আসে
    
    schedule = routine.get(today, [])
    
    if not schedule:
        await update.message.reply_text(f"আজ ({today}) কোনো ক্লাস নেই।")
    else:
        message = format_schedule(schedule, f"আজ ({today})")
        await update.message.reply_html(message)

# /tomorrow কমান্ডের ফাংশন
async def tomorrow_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routine = load_routine()
    
    # টাইমজোন ঠিক রেখে আগামীকালের তারিখ ও দিনের নাম বের করা
    tz = datetime.timezone(datetime.timedelta(hours=6))
    tomorrow_date = datetime.datetime.now(tz) + datetime.timedelta(days=1)
    tomorrow_day_name = tomorrow_date.strftime('%A')
    
    schedule = routine.get(tomorrow_day_name, [])
    
    message = format_schedule(schedule, tomorrow_day_name)
    await update.message.reply_html(message)

# বট চালানোর মূল ফাংশন
def main():
    # অ্যাপ্লিকেশন বিল্ড করা
    application = Application.builder().token(BOT_TOKEN).build()

    # কমান্ডগুলো যোগ করা
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("today", today_schedule))
    application.add_handler(CommandHandler("tomorrow", tomorrow_schedule))

    # বট চালু করা
    print("বট চালু হচ্ছে...")
    application.run_polling()

if __name__ == "__main__":
    main()
