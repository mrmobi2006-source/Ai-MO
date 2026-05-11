"""
================================================================
  handlers/admin.py  —  Admin commands & panel
================================================================
"""

from datetime import datetime

from telegram import Telegram
from vip import VipManager
from config import ADMIN_ID


def handle_admin(ctx: dict) -> bool:
    tg   = ctx["tg"]
    vip  = ctx["vip"]
    chat = ctx["chat"]
    frm  = ctx["frm"]
    mid  = ctx["mid"]
    text = ctx["text"]
    data = ctx["data"]

    # Admin panel callback
    if data == "admin_panel":
        if not vip.is_admin(frm):
            return False
        _send_admin_panel(tg, vip, chat, mid)
        return True

    # Text commands must start with /
    if not text or not text.startswith("/"):
        return False

    if not vip.is_admin(frm):
        return False

    parts = text.strip().split()
    cmd   = parts[0].lower()

    # /vip_add {user_id} {duration}
    if cmd == "/vip_add":
        if len(parts) < 3:
            tg.send_message(chat, "⚠️ الاستخدام:\n<code>/vip_add {user_id} {مدة}</code>\nأمثلة: 7d / 24h / 60m")
            return True
        uid = int(parts[1])
        sec = VipManager.parse_duration(parts[2])
        if not sec:
            tg.send_message(chat, "⚠️ صيغة المدة خاطئة. استخدم: 7d أو 24h أو 60m")
            return True
        vip.grant_vip(uid, sec, frm)
        expires = datetime.fromtimestamp(__import__("time").time() + sec).strftime("%Y-%m-%d %H:%M")
        tg.send_message(chat, f"✅ <b>تم منح VIP للمستخدم</b> <code>{uid}</code>\n⏳ ينتهي: {expires}")
        return True

    # /vip_remove {user_id}
    if cmd == "/vip_remove":
        if len(parts) < 2:
            tg.send_message(chat, "⚠️ الاستخدام: <code>/vip_remove {user_id}</code>")
            return True
        uid = int(parts[1])
        vip.revoke_vip(uid)
        tg.send_message(chat, f"✅ <b>تم إلغاء VIP للمستخدم</b> <code>{uid}</code>")
        return True

    # /vip_all {duration}
    if cmd == "/vip_all":
        if len(parts) < 2:
            tg.send_message(chat, "⚠️ الاستخدام: <code>/vip_all {مدة}</code>\nمثال: /vip_all 24h")
            return True
        sec = VipManager.parse_duration(parts[1])
        if not sec:
            tg.send_message(chat, "⚠️ صيغة المدة خاطئة.")
            return True
        vip.grant_global_vip(sec, frm)
        expires = datetime.fromtimestamp(__import__("time").time() + sec).strftime("%Y-%m-%d %H:%M")
        tg.send_message(chat, f"✅ <b>تم تفعيل VIP للجميع</b>\n⏳ ينتهي: {expires}")
        return True

    # /vip_all_remove
    if cmd == "/vip_all_remove":
        vip.revoke_global_vip()
        tg.send_message(chat, "✅ <b>تم إلغاء VIP العام للجميع</b>")
        return True

    # /admin_add {user_id}
    if cmd == "/admin_add":
        if len(parts) < 2:
            tg.send_message(chat, "⚠️ الاستخدام: <code>/admin_add {user_id}</code>")
            return True
        uid = int(parts[1])
        vip.add_admin(uid, frm)
        tg.send_message(chat, f"✅ <b>تم إضافة الأدمن</b> <code>{uid}</code>")
        return True

    # /admin_remove {user_id}
    if cmd == "/admin_remove":
        if len(parts) < 2:
            tg.send_message(chat, "⚠️ الاستخدام: <code>/admin_remove {user_id}</code>")
            return True
        uid = int(parts[1])
        if uid == ADMIN_ID:
            tg.send_message(chat, "❌ لا يمكن حذف الأدمن الرئيسي.")
            return True
        vip.remove_admin(uid)
        tg.send_message(chat, f"✅ <b>تم حذف الأدمن</b> <code>{uid}</code>")
        return True

    # /admin_list
    if cmd == "/admin_list":
        admins = vip.list_admins()
        lst    = "\n".join(f"• <code>{a}</code>" for a in admins)
        tg.send_message(chat, f"👮 <b>قائمة الأدمن:</b>\n{lst}")
        return True

    # /vip_status {user_id}
    if cmd == "/vip_status":
        if len(parts) < 2:
            tg.send_message(chat, "⚠️ الاستخدام: <code>/vip_status {user_id}</code>")
            return True
        uid    = int(parts[1])
        is_vip = vip.is_vip(uid)
        expiry = vip.get_vip_expiry(uid)
        status = "✅ VIP فعّال" if is_vip else "❌ ليس VIP"
        exp    = ""
        if expiry:
            exp = "\n⏳ ينتهي: " + datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M")
        tg.send_message(chat, f"<b>الحالة للمستخدم</b> <code>{uid}</code>:\n{status}{exp}")
        return True

    # /help_admin
    if cmd == "/help_admin":
        _send_admin_help(tg, chat)
        return True

    return False


def _send_admin_panel(tg: Telegram, vip: VipManager, chat: int, mid: int) -> None:
    global_vip = vip.get_global_vip_info()
    if global_vip:
        g_status = "✅ مفعّل حتى " + datetime.fromtimestamp(global_vip["expires_at"]).strftime("%Y-%m-%d %H:%M")
    else:
        g_status = "❌ غير مفعّل"

    text  = "⚙️ <b>لوحة الأدمن</b>\n\n"
    text += f"🌍 <b>VIP العام:</b> {g_status}\n\n"
    text += "📋 <b>الأوامر المتاحة:</b>\n"
    text += "<code>/vip_add {id} {مدة}</code> — منح VIP لشخص\n"
    text += "<code>/vip_remove {id}</code> — إلغاء VIP لشخص\n"
    text += "<code>/vip_all {مدة}</code> — VIP للجميع\n"
    text += "<code>/vip_all_remove</code> — إلغاء VIP الجميع\n"
    text += "<code>/vip_status {id}</code> — حالة مستخدم\n"
    text += "<code>/admin_add {id}</code> — إضافة أدمن\n"
    text += "<code>/admin_remove {id}</code> — حذف أدمن\n"
    text += "<code>/admin_list</code> — قائمة الأدمن\n\n"
    text += "⏱ <b>صيغة المدة:</b> <code>7d</code> / <code>24h</code> / <code>60m</code>"

    tg.send_message(chat, text, {
        "reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])
    })


def _send_admin_help(tg: Telegram, chat: int) -> None:
    tg.send_message(chat,
        "📖 <b>مساعدة الأدمن:</b>\n\n"
        "<code>/vip_add 123456789 7d</code>\nمنح VIP لمدة 7 أيام\n\n"
        "<code>/vip_add 123456789 24h</code>\nمنح VIP لمدة 24 ساعة\n\n"
        "<code>/vip_remove 123456789</code>\nإلغاء VIP لشخص\n\n"
        "<code>/vip_all 48h</code>\nتفعيل VIP للجميع لمدة 48 ساعة\n\n"
        "<code>/vip_all_remove</code>\nإلغاء VIP للجميع\n\n"
        "<code>/vip_status 123456789</code>\nمعرفة حالة مستخدم\n\n"
        "<code>/admin_add 123456789</code>\nإضافة مشرف جديد\n\n"
        "<code>/admin_remove 123456789</code>\nحذف مشرف"
    )
