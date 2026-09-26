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

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
SOURCE_CHAT = int(os.environ.get("SOURCE_CHAT", "-1002357234526"))
TARGET_CHAT = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))

YELLOW_TEXT = ("❗ <b>УВАГА</b> ❗\n🚨 ПОВІТРЯНА ТРИВОГА\n📍 Березівський район\n\n🟡 Жовтий рівень небезпеки\n🔴 Пройдіть в укриття та перебувайте там до відбою!\n\n💚 Бережіть себе та своїх близьких 🫂")
RED_TEXT = ("🔴 <b>УВАГА!</b>\nБАЛІСТИЧНА ЗАГРОЗА!\n📍 Березівський район\n\nНе ігноруйте сигнал повітряної тривоги та прямуйте в укриття.")
GREEN_TEXT = ("🟢 <b>УВАГА!</b>\nВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ\n📍 Березівський район\n\nСлідкуйте за офіційними повідомленнями.\n\nОбіймаємо вас ❤️\n🦊 Ваша команда «Бесідки»")
SILENCE_TEXT = ("🖤 <b>Хвилина мовчання</b>\nЗупинись. Помовчи. Відчуй.\n\nСьогодні ми згадуємо тих, хто віддав своє життя за наш спокій і свободу.\nЇх немає поруч, але їхня відвага живе в кожному нашому подиху.\n\nВічна пам'ять. Вічна слава Героям України.")
TEXT_ANON = ("🫣 <b>Є що розповісти, але не хочеш світити своє ім'я?</b>\n\nНадсилай нам новини, ситуації, фото, відео або просто те, що відбувається у твоєму селі чи районі — повністю анонімно 👇\n\n🤖 @BesidkaBerezivkyBot\n\n📩 Побачив(ла) щось цікаве?\n🔥 Сталося щось важливе?\n👀 Хочеш попередити інших?\n\nНе мовчи — надсилай у бот! Можливо, саме твоє повідомлення сьогодні з'явиться у «Бесідці Березівки» 💙💛")
TEXT_FRIENDS = ("Друзі! 💛\n\nЯкщо у вас є друзі або родичі з Березівки чи району — запрошуйте їх до нас! 🫶\nБудемо раді кожній людині, яка приєднається та підтримає нас.\nРазом нас буде ще більше! ❤️\nhttps://t.me/flud_bz_k\n\nБудемо раді якщо ви поділитися ❤️")
SCHEDULE = {"05:00": "anon", "19:00": "anon", "12:00": "friends", "00:00": "friends"}
SCHED_FILE = "scheduled_state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

def kyiv_now():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        return datetime.now(ZoneInfo("Europe/Kyiv"))
    except Exception:
        from datetime import datetime
        return datetime.utcnow()

def load_sched():
    import json
    try:
        with open(SCHED_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_sched(data):
    import json
    with open(SCHED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def classify(text: str):
    low = (text or "").lower()
    if "хвилина мовчання" in low:
        return "silence"
    # отбой - грубо, без привязки к і/ї
    if "відб" in low or "вiдб" in low or "отбой" in low or "отбій" in low:
        return "green"
    is_berez = "березів" in low or "березiв" in low or "березов" in low or "берез" in low
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

async def send_and_pin(client, text):
    msg = await client.send_message(TARGET_CHAT, text, parse_mode="html")
    try:
        await client.pin_message(TARGET_CHAT, msg.id, notify=False)
    except Exception as e:
        logging.warning(f"pin failed: {e}")
    return msg

async def scheduler_loop(client):
    import asyncio
    while True:
        try:
            now = kyiv_now()
            hm = now.strftime("%H:%M")
            today = now.date().isoformat()
            if hm in SCHEDULE:
                data = load_sched()
                sent = data.get(today, [])
                if hm not in sent:
                    text = TEXT_ANON if SCHEDULE[hm] == "anon" else TEXT_FRIENDS
                    await client.send_message(TARGET_CHAT, text, parse_mode="html")
                    sent.append(hm)
                    data[today] = sent
                    save_sched(data)
        except Exception as e:
            logging.warning(f"scheduler error: {e}")
        await asyncio.sleep(30)

async def main():
    start_web_stub()
    assert API_ID and API_HASH and SESSION_STRING and TARGET_CHAT, "нет секретов"
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    async def handle_text(text):
        kind = classify(text)
        logging.info(f"donor post kind={kind} preview={text[:120]!r}")
        if kind == "yellow":
            await send_and_pin(client, YELLOW_TEXT)
        elif kind == "red":
            await send_and_pin(client, RED_TEXT)
        elif kind == "green":
            await send_and_pin(client, GREEN_TEXT)
        elif kind == "silence":
            await client.send_message(TARGET_CHAT, SILENCE_TEXT, parse_mode="html")
    @client.on(events.NewMessage(chats=SOURCE_CHAT))
    async def handler(event):
        await handle_text(event.message.message or event.message.text or "")
    @client.on(events.MessageEdited(chats=SOURCE_CHAT))
    async def handler_edit(event):
        await handle_text(event.message.message or event.message.text or "")
    import asyncio as _a
    _a.create_task(scheduler_loop(client))
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
