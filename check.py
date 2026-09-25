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
    if level == prev:
        print("no change, skip")
        return
    if level == "yellow":
        await tg_send("🚨 <b>УВАГА! ПОВІТРЯНА ТРИВОГА!!!</b> 🚨\n\nУ Березівській громаді та Березівському районі оголошено ПОВІТРЯНУ ТРИВОГУ.\n\n🔴 Просимо негайно перейти до найближчого укриття та залишатися там до відбою.\n\n🟡 Жовтий рівень небезпеки · Повітряна загроза")
    elif level == "red":
        await tg_send("🚨 <b>УВАГА! РАКЕТНА НЕБЕЗПЕКА!!!</b> 🚨\n\nУ Березівській громаді оголошено підвищений рівень ПОВІТРЯНОЇ ЗАГРОЗИ.\n\n🔴 Ракетна небезпека! Негайно прямуйте до укриття!!!.\n\n🔴 Червоний рівень · Ракетна загроза!!!")
    else:
        if prev in ("yellow", "red"):
            await tg_send("🟢 <b>УВАГА! ВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ!!!</b> 🟢\n\nВІДБІЙ ПОВІТРЯНОЇ ТРИВОГИ в Березівській громаді та Березівському районі.\n\nМожна залишити укриття, але продовжуйте стежити за офіційними повідомленнями.")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"level": level}, f)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
