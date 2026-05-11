"""
================================================================
  VIP NanaBanana Bot - Main Handler (Python)
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
from handlers.chat import handle_chat

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
db  = Database()
db.init()


@app.route("/", methods=["GET"])
def index():
    if request.args.get("test") is not None:
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

    threading.Thread(target=_process_update, args=(update,), daemon=True).start()
    return "ok", 200


def _process_update(update: dict):
    try:
        tg  = Telegram(BOT_TOKEN)
        vip = VipManager(db)

        msg   = update.get("message")
        cbq   = update.get("callback_query")
        chat  = frm = mid = text = data = photo = cbid = None

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

        if cbq and cbid:
            tg.call("answerCallbackQuery", {"callback_query_id": cbid})

        # حماية التكرار
        if msg and text:
            h = hashlib.md5(f"{chat}_{text}_{msg.get('message_id','')}".encode()).hexdigest()
            if not db.check_and_insert_request(h):
                return

        if not db.is_user_free(frm):
            return

        state_file = os.path.join("data", f"{frm}.json")
        state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = {}

        ctx = dict(
            tg=tg, vip=vip, db=db,
            chat=chat, frm=frm, mid=mid,
            text=text, data=data, photo=photo,
            state=state, state_file=state_file,
            cbq=cbq, msg=msg,
        )

        # أوامر الأدمن
        if text and text.startswith("/") and handle_admin(ctx):
            return

        if data == "admin_panel":
            handle_admin(ctx)
            return

        # /start
        if text == "/start":
            handle_start(ctx)
            return

        if data == "back":
            handle_start(ctx, is_back=True)
            return

        # الصور
        if handle_image(ctx):
            return

        # الفيديو
        if handle_video(ctx):
            return

        # المحادثة الذكية
        if handle_chat(ctx):
            return

        # fallback
        if text and not os.path.exists(state_file):
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
