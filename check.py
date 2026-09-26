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

SILENCE_TEXT = (
    "🖤 <b>Хвилина мовчання</b>\n"
    "Зупинись. Помовчи. Відчуй.\n\n"
    "Сьогодні ми згадуємо тих, хто віддав своє життя за наш спокій і свободу.\n"
    "Їх немає поруч, але їхня відвага живе в кожному нашому подиху.\n\n"
    "Вічна пам'ять. Вічна слава Героям України."
)

def should_send_silence():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        now = datetime.now(ZoneInfo("Europe/Kyiv"))
    except Exception:
        from datetime import datetime
        now = datetime.utcnow()
    if now.hour != 9 or now.minute >= 5:
        return False
    today = now.date().isoformat()
    try:
        with open(SILENCE_FILE, encoding="utf-8") as f:
            if json.load(f).get("date") == today:
                return False
    except FileNotFoundError:
        pass
    return True

def mark_silence_sent():
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        today = datetime.now(ZoneInfo("Europe/Kyiv")).date().isoformat()
    except Exception:
        from datetime import datetime
        today = datetime.utcnow().date().isoformat()
    with open(SILENCE_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today}, f)

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
        if RAION_KEYWORD in raion and a.get("alert_type") == "air_raid":
            if a.get("location_type") == "raion":
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
    threats = alert.get("threats") or []
    levels = [t.get("level") for t in threats if t.get("level") in ("red", "yellow")]
    if "red" in levels:
        return "red"
    if "yellow" in levels:
        return "yellow"
    return "red"

async def tg_send(text):
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        await client.send_message(CHAT_ID, text, parse_mode="html")

async def main():
    assert ALERTS_TOKEN and API_ID and API_HASH and SESSION_STRING and CHAT_ID, "нет секретов"
    alerts = get_active()
    found = find_relevant(alerts)
    level = get_level(found)
    prev = "unknown"
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            prev = json.load(f).get("level", "unknown")
    except FileNotFoundError:
        pass
    print(f"now={level} prev={prev} matched={found['location_title'] if found else '-'}")
    if level != prev:
        if level == "yellow":
            await tg_send("❗ <b>УВАГА</b> ❗\n🚨 ПОВІТРЯНА ТРИВОГА\n📍 Березівський район\n\n🟡 Жовтий рівень небезпеки\n🔴 Пройдіть в укриття та перебувайте там до відбою!\n\n💚 Бережіть себе та своїх близьких 🫂")
        elif level == "red":
            await tg_send("🔴 <b>УВАГА!</b>\nБАЛІСТИЧНА ЗАГРОЗА!\n📍 Березівський район\n\nНе ігноруйте сигнал повітряної тривоги та прямуйте в укриття.")
        else:
            if prev in ("yellow", "red"):
                await tg_send("🟢 <b>УВАГА!</b>\nВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ\n📍 Березівський район\n\nСлідкуйте за офіційними повідомленнями.\n\nОбіймаємо вас ❤️\n🦊 Ваша команда «Бесідки»")
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"level": level}, f)
    else:
        print("no change, skip")
    if should_send_silence():
        print("sending silence")
        await tg_send(SILENCE_TEXT)
        mark_silence_sent()
    else:
        print("silence skip")

if __name__ == "__main__":
    asyncio.run(main())
