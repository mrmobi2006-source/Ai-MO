"""
================================================================
  handlers/start.py  —  /start & main menu
================================================================
"""

import os
from datetime import datetime

from telegram import Telegram
from config import WELCOME_PHOTO


def handle_start(ctx: dict, is_back: bool = False) -> None:
    tg         = ctx["tg"]
    vip        = ctx["vip"]
    chat       = ctx["chat"]
    frm        = ctx["frm"]
    mid        = ctx["mid"]
    cbq        = ctx["cbq"]
    state_file = ctx["state_file"]

    # مسح أي state موجود
    if os.path.exists(state_file):
        os.remove(state_file)

    is_vip   = vip.is_vip(frm)
    is_admin = vip.is_admin(frm)

    vip_badge  = " ⭐" if is_vip else ""
    expiry     = vip.get_vip_expiry(frm)
    expiry_txt = ""
    if expiry:
        expiry_txt = "\n<b>⏳ VIP حتى:</b> " + datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M")

    cap  = f"<b>مرحباً بك في بوت NanaBanana{vip_badge}</b>\n"
    cap += "<b>نقدم لك أفضل حلول الذكاء الاصطناعي بأعلى جودة 🚀</b>"
    cap += expiry_txt

    rows = []

    if is_vip:
        rows.append([
            Telegram.btn("🖼 إنشاء صورة", "create_image"),
            Telegram.btn("✏️ تعديل صورة", "edit_image"),
        ])
        rows.append([
            Telegram.btn("🎬 نص ← فيديو",   "text_to_video"),
            Telegram.btn("🖼 صورة ← فيديو", "image_to_video"),
        ])
        rows.append([
            Telegram.btn("🤖 محادثة ذكية", "ai_chat"),
        ])
    else:
        cap += "\n\n<b>🔒 هذا البوت VIP فقط.</b>\nتواصل مع الأدمن للحصول على صلاحية."

    if is_admin:
        rows.append([Telegram.btn("⚙️ لوحة الأدمن", "admin_panel")])

    extra = {
        "has_spoiler":  "true",
        "reply_markup": Telegram.kb(rows),
    }

    if is_back and cbq:
        tg.delete_message(chat, mid)

    tg.send_photo(chat, WELCOME_PHOTO, cap, extra)
