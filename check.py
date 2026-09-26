import os
import json
import urllib.request
import asyncio
from telethon.sessions import StringSession
from telethon import TelegramClient

ALERTS_TOKEN = os.environ.get("ALERTS_TOKEN", "")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
TARGET_UID = os.environ.get("TARGET_UID", "434")
OBLAST_NAME = "Одеська область"
RAION_KEYWORD = "Березівський"
STATE_FILE = "state.json"
SILENCE_FILE = "silence_state.json"
SCHED_FILE = "scheduled_state.json"

YELLOW_TEXT = ("❗ <b>УВАГА</b> ❗\n🚨 ПОВІТРЯНА ТРИВОГА\n📍 Березівський район\n\n🟡 Жовтий рівень небезпеки\n🔴 Пройдіть в укриття та перебувайте там до відбою!\n\n💚 Бережіть себе та своїх близьких 🫂")
RED_TEXT = ("🔴 <b>УВАГА!</b>\nБАЛІСТИЧНА ЗАГРОЗА!\n📍 Березівський район\n\nНе ігноруйте сигнал повітряної тривоги та прямуйте в укриття.")
GREEN_TEXT = ("🟢 <b>УВАГА!</b>\nВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ\n📍 Березівський район\n\nСлідкуйте за офіційними повідомленнями.\n\nОбіймаємо вас ❤️\n🦊 Ваша команда «Бесідки»")
SILENCE_TEXT = ("🖤 <b>Хвилина мовчання</b>\nЗупинись. Помовчи. Відчуй.\n\nСьогодні ми згадуємо тих, хто віддав своє життя за наш спокій і свободу.\nЇх немає поруч, але їхня відвага живе в кожному нашому подиху.\n\nВічна пам'ять. Вічна слава Героям України.")
TEXT_ANON = ("🫣 <b>Є що розповісти, але не хочеш світити своє ім'я?</b>\n\nНадсилай нам новини, ситуації, фото, відео або просто те, що відбувається у твоєму селі чи районі — повністю анонімно 👇\n\n🤖 @BesidkaBerezivkyBot\n\n📩 Побачив(ла) щось цікаве?\n🔥 Сталося щось важливе?\n👀 Хочеш попередити інших?\n\nНе мовчи — надсилай у бот! Можливо, саме твоє повідомлення сьогодні з'явиться у «Бесідці Березівки» 💙💛")
TEXT_FRIENDS = ("Друзі! 💛\n\nЯкщо у вас є друзі або родичі з Березівки чи району — запрошуйте їх до нас! 🫶\nБудемо раді кожній людині, яка приєднається та підтримає нас.\nРазом нас буде ще більше! ❤️\nhttps://t.me/flud_bz_k\n\nБудемо раді якщо ви поділитися ❤️")
SCHEDULE = {"05:00": "anon", "19:00": "anon", "12:00": "friends", "00:00": "friends"}

def kyiv_now():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        return datetime.now(ZoneInfo("Europe/Kyiv"))
    except Exception:
        from datetime import datetime
        return datetime.utcnow()

def get_active():
    url = "https://api.alerts.in.ua/v1/alerts/active.json"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {ALERTS_TOKEN}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "ignore")).get("alerts", [])

def find_relevant(alerts):
    for a in alerts:
        if str(a.get("location_uid", "")) == str(TARGET_UID) and a.get("alert_type") == "air_raid":
            return a
    for a in alerts:
        raion = (a.get("location_raion") or "") + " " + (a.get("location_title") or "")
        if RAION_KEYWORD in raion and a.get("alert_type") == "air_raid" and a.get("location_type") == "raion":
            return a
    for a in alerts:
        if a.get("location_title") == OBLAST_NAME and a.get("location_type") == "oblast" and a.get("alert_type") == "air_raid":
            return a
    return None

def get_level(alert):
    if not alert:
        return "none"
    lvl = alert.get("alert_level")
    if lvl in ("red", "yellow"):
        return lvl
    levels = [t.get("level") for t in (alert.get("threats") or []) if t.get("level") in ("red", "yellow")]
    if "red" in levels:
        return "red"
    if "yellow" in levels:
        return "yellow"
    return "red"

async def tg_send(client, text):
    await client.send_message(CHAT_ID, text, parse_mode="html")

async def main():
    assert ALERTS_TOKEN and API_ID and API_HASH and SESSION_STRING and CHAT_ID, "нет секретов"
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        alerts = get_active()
        level = get_level(find_relevant(alerts))
        prev = "unknown"
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                prev = json.load(f).get("level", "unknown")
        except FileNotFoundError:
            pass
        print(f"now={level} prev={prev}")
        if level != prev:
            if level == "yellow":
                await tg_send(client, YELLOW_TEXT)
            elif level == "red":
                await tg_send(client, RED_TEXT)
            elif prev in ("yellow", "red"):
                await tg_send(client, GREEN_TEXT)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"level": level}, f)
        now = kyiv_now()
        hm = now.strftime("%H:%M")
        today = now.date().isoformat()
        if hm == "09:00" or (hm.startswith("09:0") and now.minute <= 4):
            try:
                with open(SILENCE_FILE, encoding="utf-8") as f:
                    done = json.load(f).get("date") == today
            except FileNotFoundError:
                done = False
            if not done:
                await tg_send(client, SILENCE_TEXT)
                with open(SILENCE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"date": today}, f)
        if hm in SCHEDULE:
            try:
                with open(SCHED_FILE, encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {}
            sent = data.get(today, [])
            if hm not in sent:
                await tg_send(client, TEXT_ANON if SCHEDULE[hm] == "anon" else TEXT_FRIENDS)
                sent.append(hm)
                data[today] = sent
                with open(SCHED_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f)

if __name__ == "__main__":
    asyncio.run(main())
