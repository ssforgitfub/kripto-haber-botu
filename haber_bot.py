import time
import hashlib
import sqlite3
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === CONFIG ===
TOKEN = "8596940961:AAFVK9GKpgKg3LSdBWaX9adzhahwdTUx1o8"
GROUP_CHAT_ID = -1003268398528  # <--- BURAYA ASIL GRUBUN ID'SINI YAZ

SOURCES = [
    {"name": "CoingraphNews", "username": "CoingraphNews"},
    {"name": "CoinDesk", "username": "coindesk"},
]

# KALICI CACHE DOSYASI
DB_FILE = "/opt/render/project/src/cache.db"  # Render'da kalıcı yol
db = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS seen (hash TEXT PRIMARY KEY, timestamp INTEGER)''')
db.commit()

translator = Translator()

def get_channel_posts(username):
    url = f"https://t.me/s/{username}"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        posts = []
        for post in soup.find_all('div', class_='tgme_widget_message')[-3:]:
            text_div = post.find('div', class_='tgme_widget_message_text')
            link_tag = post.find('a', class_='tgme_widget_message_date')
            if text_div and link_tag:
                text = text_div.get_text().strip()
                text = text.split("Telegram |")[0].strip()
                text = text.split("https://t.me/")[0].strip()
                text = text.split("t.me/")[0].strip()
                text = ' '.join(text.split())
                
                link = "https://t.me" + link_tag['href']
                content = f"{text}{link}"
                hash_id = hashlib.md5(content.encode()).hexdigest()
                
                # ZATEN VAR MI?
                cursor.execute("SELECT 1 FROM seen WHERE hash=?", (hash_id,))
                if cursor.fetchone():
                    continue
                
                posts.append({"text": text, "link": link, "hash": hash_id, "source": username})
        return posts
    except Exception as e:
        print(f"Scraping hatası ({username}): {e}")
        return []

def get_news():
    all_posts = []
    for src in SOURCES:
        posts = get_channel_posts(src["username"])
        for p in posts:
            p["source_name"] = src["name"]
            all_posts.append(p)
    return all_posts

async def haber_gonder(context: ContextTypes.DEFAULT_TYPE):
    news = get_news()
    if not news:
        return
    for item in news:
        try:
            tr_text = translator.translate(item["text"], dest='tr').text
            message = (
                f"*{item['source_name']}*\n\n"
                f"*{tr_text}*\n\n"
                f"Kaynak: {item['link']}"
            )
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            # CACHE'E EKLE
            cursor.execute("INSERT INTO seen (hash, timestamp) VALUES (?, ?)", 
                         (
