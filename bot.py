import telebot
from telebot import types
import requests

# ----------------- تنظیمات -----------------
TOKEN = "8403027857:AAEHINZ5ATTnm1ZNqlIjWEBpbzKPtkHRSOI"
OMDB_API_KEY = "69de55af"

# آیدی کانال‌هات (حتماً با -100 شروع بشه)
CHANNEL_IDS = [
    -1001514472310,
    -1001136219223
]

bot = telebot.TeleBot(TOKEN)

# ----------------- چک عضویت -----------------
def is_member(user_id):
    for cid in CHANNEL_IDS:
        try:
            member = bot.get_chat_member(cid, user_id)
            if member.status in ["member", "administrator", "creator"]:
                continue
            else:
                return False
        except Exception as e:
            print(f"❌ Error checking membership: {e}")
            return False
    return True

# ----------------- سرچ در OMDb -----------------
def omdb_search(query):
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&s={query}"
    r = requests.get(url)
    data = r.json()
    if data.get("Response") == "True":
        return data["Search"]
    return []

def omdb_details(imdb_id):
    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}&plot=full"
    r = requests.get(url)
    return r.json()

# ----------------- هندل پیام -----------------
@bot.message_handler(func=lambda m: True)
def handle_query(m):
    uid = m.from_user.id

    if not is_member(uid):
        join_links = "\n".join([f"https://t.me/{str(cid)[4:]}" for cid in CHANNEL_IDS])
        bot.send_message(uid, f"🔒 برای استفاده از ربات باید عضو همه کانال‌ها بشی:\n{join_links}")
        return

    query = m.text.strip()
    bot.send_message(uid, "⏳ در حال جستجو...")

    results = omdb_search(query)
    if not results:
        bot.send_message(uid, "❌ نتیجه‌ای پیدا نشد. اسم دقیق‌تر وارد کن.")
        return

    markup = types.InlineKeyboardMarkup()
    for item in results[:10]:  # حداکثر ۱۰ نتیجه
        label = f"{item['Title']} ({item['Year']})"
        cb = f"select|{item['imdbID']}"
        markup.add(types.InlineKeyboardButton(label, callback_data=cb))

    bot.send_message(uid, "🎬 نتایج پیدا شد — یکی رو انتخاب کن:", reply_markup=markup)

# ----------------- هندل انتخاب -----------------
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("select|"))
def callback_select(call):
    uid = call.from_user.id
    imdb_id = call.data.split("|")[1]

    movie = omdb_details(imdb_id)
    if movie.get("Response") != "True":
        bot.send_message(uid, "❌ خطا در دریافت اطلاعات.")
        return

    title = movie.get("Title", "Unknown")
    year = movie.get("Year", "")
    plot = movie.get("Plot", "بدون توضیح")
    poster = movie.get("Poster")

    caption = f"🎬 {title} ({year})\n\n{plot}"

    if poster and poster != "N/A":
        bot.send_photo(uid, poster, caption=caption)
    else:
        bot.send_message(uid, caption)

    # اگر سریال بود، اپیزودها رو بیاره
    if movie.get("Type") == "series":
        markup = types.InlineKeyboardMarkup()
        for season in range(1, 6):  # فعلاً ۵ فصل اول
            cb = f"season|{imdb_id}|{season}"
            markup.add(types.InlineKeyboardButton(f"📺 Season {season}", callback_data=cb))
        bot.send_message(uid, "👉 یک فصل انتخاب کن:", reply_markup=markup)

# ----------------- هندل فصل -----------------
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("season|"))
def callback_season(call):
    uid = call.from_user.id
    _, imdb_id, season = call.data.split("|")

    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}&Season={season}"
    r = requests.get(url).json()

    if r.get("Response") != "True":
        bot.send_message(uid, "❌ اپیزودی پیدا نشد.")
        return

    episodes = r.get("Episodes", [])
    markup = types.InlineKeyboardMarkup()
    for ep in episodes:
        ep_title = ep.get("Title", "Unknown")
        ep_num = ep.get("Episode")
        cb = f"episode|{imdb_id}|{season}|{ep_num}"
        markup.add(types.InlineKeyboardButton(f"Ep {ep_num}: {ep_title}", callback_data=cb))

    bot.send_message(uid, f"📺 فصل {season} — انتخاب کن:", reply_markup=markup)

# ----------------- هندل اپیزود -----------------
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("episode|"))
def callback_episode(call):
    uid = call.from_user.id
    _, imdb_id, season, ep_num = call.data.split("|")

    url = f"http://www.omdbapi.com/?apikey={OMDB_API_KEY}&i={imdb_id}&Season={season}&Episode={ep_num}"
    ep = requests.get(url).json()

    if ep.get("Response") != "True":
        bot.send_message(uid, "❌ اپیزود پیدا نشد.")
        return

    title = ep.get("Title", "Unknown")
    released = ep.get("Released", "N/A")
    plot = ep.get("Plot", "بدون توضیح")

    caption = f"📺 {title}\n📅 {released}\n\n{plot}"
    bot.send_message(uid, caption)

# ----------------- شروع -----------------
print("✅ Bot started...")
bot.infinity_polling()
