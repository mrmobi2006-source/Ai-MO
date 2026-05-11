"""
================================================================
  VIP NanaBanana Bot - Main Handler (Python)
  Runs via Gunicorn with multiple workers for concurrency.
================================================================
"""

import os
import json
import hashlib
import logging
import threading
from flask import Flask, request, jsonify

from database import Database
from vip import VipManager
from telegram import Telegram
from config import BOT_TOKEN, BOT_USERNAME
from handlers.start import handle_start
from handlers.image import handle_image
from handlers.video import handle_video
from handlers.admin import handle_admin

# ── Logging ──────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/error.log"),
        logging.StreamHandler(),
    ],
)

app = Flask(__name__)

# ── Bootstrap DB ─────────────────────────────────────────────
db = Database()
db.init()


@app.route("/", methods=["GET"])
def index():
    test = request.args.get("test")
    if test is not None:
        return jsonify({"status": "ok", "bot": BOT_USERNAME})
    return "NanaBanana VIP Bot is running 🍌", 200


@app.route("/", methods=["POST"])
def webhook():
    body = request.get_data(as_text=True)
    if not body:
        return "ok", 200

    try:
        update = json.loads(body)
    except json.JSONDecodeError:
        return "ok", 200

    # ── نعالج الطلب في thread منفصل ──────────────────────────
    # هذا يجعل webhook يرد فوراً لتيليغرام (200 OK)
    # بينما يُعالَج الطلب الثقيل (فيديو/صورة) في الخلفية
    t = threading.Thread(target=_process_update, args=(update,), daemon=True)
    t.start()

    return "ok", 200


def _process_update(update: dict):
    """معالجة الـ update في thread منفصل."""
    try:
        tg  = Telegram(BOT_TOKEN)
        vip = VipManager(db)

        msg   = update.get("message")
        cbq   = update.get("callback_query")
        chat  = None
        frm   = None
        mid   = None
        text  = None
        data  = None
        photo = None
        cbid  = None

        if msg:
            chat  = msg.get("chat", {}).get("id")
            frm   = msg.get("from", {}).get("id")
            mid   = msg.get("message_id")
            text  = msg.get("text")
            photo = msg.get("photo")
        if cbq:
            chat  = chat or cbq.get("message", {}).get("chat", {}).get("id")
            frm   = frm  or cbq.get("from", {}).get("id")
            mid   = mid  or cbq.get("message", {}).get("message_id")
            data  = cbq.get("data")
            cbid  = cbq.get("id")

        if not frm or not chat:
            return

        # Answer callback immediately
        if cbq and cbid:
            tg.call("answerCallbackQuery", {"callback_query_id": cbid})

        # ── Duplicate guard ───────────────────────────────────
        if msg and text:
            raw = f"{chat}_{text}_{msg.get('message_id', '')}"
            h   = hashlib.md5(raw.encode()).hexdigest()
            if not db.check_and_insert_request(h):
                return

        # ── Busy guard ────────────────────────────────────────
        if not db.is_user_free(frm):
            return

        # ── State ─────────────────────────────────────────────
        state_file = os.path.join("data", f"{frm}.json")
        state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}

        # ── Route ─────────────────────────────────────────────
        ctx = dict(
            tg=tg, vip=vip, db=db,
            chat=chat, frm=frm, mid=mid,
            text=text, data=data, photo=photo,
            state=state, state_file=state_file,
            cbq=cbq, msg=msg,
        )

        # Admin commands
        if text and text.startswith("/") and handle_admin(ctx):
            return

        # Admin panel callback
        if data == "admin_panel":
            handle_admin(ctx)
            return

        # /start
        if text == "/start":
            handle_start(ctx)
            return

        # Back button
        if data == "back":
            handle_start(ctx, is_back=True)
            return

        # Image flow
        if handle_image(ctx):
            return

        # Video flow
        if handle_video(ctx):
            return

        # Fallback
        if text and text != "/start" and not os.path.exists(state_file):
            tg.call("sendMessage", {
                "chat_id":    chat,
                "text":       "👋 <b>أهلاً! اضغط Start لتبدأ.</b>",
                "parse_mode": "HTML",
                "reply_markup": json.dumps({
                    "inline_keyboard": [[{"text": "• Start •", "callback_data": "back"}]]
                }),
            })

    except Exception as e:
        logging.error("_process_update error: %s", e, exc_info=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
