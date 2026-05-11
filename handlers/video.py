"""
================================================================
  handlers/video.py  —  Video generation flow
  (text-to-video & image-to-video)
================================================================
"""

import json
import os
import re
import logging
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from telegram import Telegram
from config import VIDEO_API_URL, LOADING_STICKER

logger = logging.getLogger(__name__)

VID_MODELS = {
    "veo-3.1-lite": "Veo 3.1 Lite (8s)",
    "sora-2":        "Sora 2 (12s)",
}

VID_RATIOS = {"16:9": "16:9", "9:16": "9:16", "1:1": "1:1"}


def handle_video(ctx: dict) -> bool:
    tg         = ctx["tg"]
    vip        = ctx["vip"]
    db         = ctx["db"]
    chat       = ctx["chat"]
    frm        = ctx["frm"]
    mid        = ctx["mid"]
    text       = ctx["text"]
    data       = ctx["data"]
    photo      = ctx["photo"]
    state      = ctx["state"]
    state_file = ctx["state_file"]

    # ── text_to_video / image_to_video ────────────────────────
    if data in ("text_to_video", "image_to_video"):
        if not vip.is_vip(frm):
            tg.send_message(chat, "🔒 هذه الميزة للأعضاء VIP فقط.")
            return True
        mode = "text" if data == "text_to_video" else "image"
        _save_state(state_file, {"type": "video", "mode": mode, "step": "choose_model"})
        _vid_send_model_menu(tg, chat, mid, mode)
        return True

    # ── Choose model ──────────────────────────────────────────
    if data and data.startswith("vid_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_ratio"})
        _save_state(state_file, state)
        _vid_send_ratio_menu(tg, chat, mid)
        return True

    # ── Choose ratio ──────────────────────────────────────────
    if data and data.startswith("vid_ratio|"):
        ratio = data.split("|")[1]
        state.update({"ratio": ratio})
        mode = state.get("mode", "text")
        md   = VID_MODELS.get(state.get("model", ""), state.get("model", ""))

        if mode == "text":
            state["step"] = "awaiting_text"
            _save_state(state_file, state)
            tg.edit_caption(
                chat, mid,
                f"<b>🎬 الموديل:</b> {md}\n<b>النسبة:</b> {ratio}\n\n✍️ <b>أرسل النص لإنشاء الفيديو:</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
            )
        else:
            state["step"] = "awaiting_image"
            _save_state(state_file, state)
            tg.edit_caption(
                chat, mid,
                f"<b>🎬 الموديل:</b> {md}\n<b>النسبة:</b> {ratio}\n\n📸 <b>أرسل الصورة لتحويلها إلى فيديو:</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
            )
        return True

    # ── Receive image for image-to-video ─────────────────────
    if state.get("step") == "awaiting_image" and state.get("type") == "video" and photo:
        fid  = photo[-1]["file_id"]
        link = tg.get_file(fid)
        if link:
            state.update({"image": link, "step": "awaiting_text_img_vid"})
            _save_state(state_file, state)
            tg.send_message(
                chat,
                "✅ <b>تم استلام الصورة!</b>\nالآن أرسل نصاً يصف الحركة أو المشهد للفيديو:",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
            )
        return True

    # ── Receive text → generate video ────────────────────────
    step = state.get("step", "")
    typ  = state.get("type", "")
    if typ == "video" and step in ("awaiting_text", "awaiting_text_img_vid") and text and text != "/start":
        if not db.is_user_free(frm):
            return True
        db.lock_user(frm)
        cur = dict(state)
        if os.path.exists(state_file):
            os.remove(state_file)

        stk    = tg.send_sticker(chat, LOADING_STICKER)
        stk_id = stk.get("result", {}).get("message_id")

        result = _call_video_api(cur, text)

        if stk_id:
            tg.delete_message(chat, stk_id)

        kb = Telegram.kb([[Telegram.btn("• رجوع •", "back")]])

        if result and result.get("status") == "success" and result.get("video_url"):
            md  = VID_MODELS.get(cur.get("model", ""), cur.get("model", ""))
            dur = result.get("duration", "?")
            cap = f"✅ <b>الموديل:</b> {md}\n<b>المدة:</b> {dur}s | <b>النسبة:</b> {cur.get('ratio')}"
            tg.send_video(chat, result["video_url"], cap, {"reply_markup": kb})
        else:
            err = result.get("message", "خطأ غير معروف") if result else "تعذر الاتصال بالخادم"
            tg.send_message(chat, f"⚠️ <b>حدث خطأ:</b> {err}", {"reply_markup": kb})

        db.unlock_user(frm)
        return True

    return False


# ── Video API call with AES cookie decryption ─────────────────
def _call_video_api(cur: dict, prompt: str) -> dict | None:
    session_cookie = _init_video_session()

    params = {
        "action": "video",
        "p":      prompt,
        "m":      cur.get("model", "veo-3.1-lite"),
        "r":      cur.get("ratio", "16:9"),
    }
    if cur.get("image"):
        params["img"] = cur["image"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    if session_cookie:
        headers["Cookie"] = session_cookie

    try:
        resp = requests.get(
            VIDEO_API_URL,
            params=params,
            headers=headers,
            timeout=180,
            verify=False,
        )
        return resp.json()
    except Exception as e:
        logger.error("Video API error: %s", e)
        return None


def _init_video_session() -> str:
    """Fetch the video page and decrypt the AES-encoded __test cookie."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(VIDEO_API_URL, headers=headers, timeout=15, verify=False)
        body = resp.text

        # Extract all hex strings passed to toNumbers()
        matches = re.findall(r'toNumbers\("([a-f0-9]+)"\)', body)
        if len(matches) >= 3:
            key = bytes.fromhex(matches[0])
            iv  = bytes.fromhex(matches[1])
            enc = bytes.fromhex(matches[2])

            cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            dec       = decryptor.update(enc) + decryptor.finalize()
            cookie_val = dec.hex()
            return f"__test={cookie_val}"
    except Exception as e:
        logger.error("Video session init error: %s", e)
    return ""


# ── Menu helpers ──────────────────────────────────────────────
def _vid_send_model_menu(tg: Telegram, chat: int, mid: int, mode: str) -> None:
    rows  = [[Telegram.btn(v, f"vid_model|{k}")] for k, v in VID_MODELS.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    title = "🎬 نص ← فيديو" if mode == "text" else "🖼 صورة ← فيديو"
    tg.edit_caption(chat, mid, f"<b>{title}\n\n🤖 اختر الموديل:</b>", {"reply_markup": Telegram.kb(rows)})


def _vid_send_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    row  = [Telegram.btn(v, f"vid_ratio|{k}") for k, v in VID_RATIOS.items()]
    rows = [row, [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>📐 اختر نسبة الفيديو:</b>", {"reply_markup": Telegram.kb(rows)})


def _save_state(path: str, data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
