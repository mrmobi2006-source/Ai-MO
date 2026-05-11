"""
================================================================
  setup.py  —  Set / delete / inspect the Telegram webhook.
  Run once after deployment:
    python setup.py set https://YOUR-APP.railway.app
    python setup.py info
    python setup.py delete
================================================================
"""

import sys
import json

from config import BOT_TOKEN, BOT_USERNAME
from telegram import Telegram

tg = Telegram(BOT_TOKEN)

cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

if cmd == "set":
    url = sys.argv[2].rstrip("/") + "/" if len(sys.argv) > 2 else ""
    if not url:
        print("Usage: python setup.py set https://YOUR-APP.railway.app")
        sys.exit(1)
    result = tg.set_webhook(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))

elif cmd == "delete":
    result = tg.call("deleteWebhook")
    print(json.dumps(result, ensure_ascii=False, indent=2))

elif cmd == "info":
    result = tg.call("getWebhookInfo")
    print(json.dumps(result, ensure_ascii=False, indent=2))

else:
    print(f"""
⚙️  NanaBanana Bot — Webhook Setup
Bot: {BOT_USERNAME}

Usage:
  python setup.py set   https://YOUR-APP.railway.app   # تفعيل
  python setup.py info                                  # معلومات
  python setup.py delete                                # حذف
""")
