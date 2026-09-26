import os
import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon.sessions import StringSession
from telethon import TelegramClient, events

def start_web_stub():
    port = int(os.environ.get("PORT", "10000"))
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        def log_message(self, *a):
            pass
    t = threading.Thread(target=HTTPServer(("0.0.0.0", port), H).serve_forever, daemon=True)
    t.start()
    logging.info(f"web stub on {port}")

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
SOURCE_CHAT = int(os.environ.get("SOURCE_CHAT", "-1002357234526"))
TARGET_CHAT = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))

YELLOW_TEXT = ("❗ <b>УВАГА</b> ❗\n🚨 ПОВІТРЯНА ТРИВОГА\n📍 Березівський район\n\n🟡 Жовтий рівень небезпеки\n🔴 Пройдіть в укриття та перебувайте там до відбою!\n\n💚 Бережіть себе та своїх близьких 🫂")
RED_TEXT = ("🔴 <b>УВАГА!</b>\nБАЛІСТИЧНА ЗАГРОЗА!\n📍 Березівський район\n\nНе ігноруйте сигнал повітряної тривоги та прямуйте в укриття.")
GREEN_TEXT = ("🟢 <b>УВАГА!</b>\nВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ\n📍 Березівський район\n\nСлідкуйте за офіційними повідомленнями.\n\nОбіймаємо вас ❤️\n🦊 Ваша команда «Бесідки»")
SILENCE_TEXT = ("🖤 <b>Хвилина мовчання</b>\nЗупинись. Помовчи. Відчуй.\n\nСьогодні ми згадуємо тих, хто віддав своє життя за наш спокій і свободу.\nЇх немає поруч, але їхня відвага живе в кожному нашому подиху.\n\nВічна пам'ять. Вічна слава Героям України.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

def classify(text: str):
    low = (text or "").lower()
    if "хвилина мовчання" in low:
        return "silence"
    is_berez = "березів" in low or "березiв" in low or "березов" in low
    if "відбій" in low or "відбiй" in low:
        return "green" if (is_berez or "відбій повітряної тривоги" in low) else None
    if not is_berez:
        if "одеська область" not in low and "одесская область" not in low:
            return None
    if "червоний рівень" in low or "ракетна загроза" in low or "балістична" in low or "баллистич" in low:
        return "red"
    if "жовтий рівень" in low or "дронова загроза" in low:
        return "yellow"
    if "повітряна тривога" in low or "повiтряна тривога" in low:
        return "yellow"
    return None

async def main():
    start_web_stub()
    assert API_ID and API_HASH and SESSION_STRING and TARGET_CHAT, "нет секретов"
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    @client.on(events.NewMessage(chats=SOURCE_CHAT))
    async def handler(event):
        text = event.message.message or ""
        kind = classify(text)
        logging.info(f"new post kind={kind}")
        if kind == "yellow":
            await client.send_message(TARGET_CHAT, YELLOW_TEXT, parse_mode="html")
        elif kind == "red":
            await client.send_message(TARGET_CHAT, RED_TEXT, parse_mode="html")
        elif kind == "green":
            await client.send_message(TARGET_CHAT, GREEN_TEXT, parse_mode="html")
        elif kind == "silence":
            await client.send_message(TARGET_CHAT, SILENCE_TEXT, parse_mode="html")
    logging.info("listener online, waiting 1-10 sec posts...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
