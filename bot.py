"""
================================================================
  VIP NanaBanana Bot - Main Handler (Python)
  Set webhook to your deployed URL after launch.
================================================================
"""

import os
import json
import hashlib
import logging
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

    tg  = Telegram(BOT_TOKEN)
    vip = VipManager(db)

    msg  = update.get("message")
    cbq  = update.get("callback_query")
    chat = None
    frm  = None
    mid  = None
    text = None
    data = None
    photo = None
    cbid = None

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
        return "ok", 200

    # Answer callback immediately
    if cbq and cbid:
        tg.call("answerCallbackQuery", {"callback_query_id": cbid})

    # ── Duplicate guard ───────────────────────────────────────
    if msg and text:
        raw = f"{chat}_{text}_{msg.get('message_id', '')}"
        h   = hashlib.md5(raw.encode()).hexdigest()
        if not db.check_and_insert_request(h):
            return "ok", 200

    # ── Busy guard ────────────────────────────────────────────
    if not db.is_user_free(frm):
        return "ok", 200

    # ── State ─────────────────────────────────────────────────
    state_file = os.path.join("data", f"{frm}.json")
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    # ── Route ─────────────────────────────────────────────────
    ctx = dict(
        tg=tg, vip=vip, db=db,
        chat=chat, frm=frm, mid=mid,
        text=text, data=data, photo=photo,
        state=state, state_file=state_file,
        cbq=cbq, msg=msg,
    )

    # Admin commands (text starting with /)
    if text and text.startswith("/") and handle_admin(ctx):
        return "ok", 200

    # Admin panel callback
    if data == "admin_panel":
        handle_admin(ctx)
        return "ok", 200

    # /start
    if text == "/start":
        handle_start(ctx)
        return "ok", 200

    # Back button
    if data == "back":
        handle_start(ctx, is_back=True)
        return "ok", 200

    # Image flow
    if handle_image(ctx):
        return "ok", 200

    # Video flow
    if handle_video(ctx):
        return "ok", 200

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

    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
