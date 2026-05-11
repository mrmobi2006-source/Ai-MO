"""
================================================================
  handlers/video.py  —  Video generation
  يجرب VIDEO_API_URL الأصلي أولاً، ثم Fal.ai كبديل
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
from config import VIDEO_API_URL, FAL_API_KEY, LOADING_STICKER

logger = logging.getLogger(__name__)

# ── النموذج الأصلي ────────────────────────────────────────────
ORIG_MODELS = {
    "veo-3.1-lite": "Veo 3.1 Lite (8s)",
    "sora-2":        "Sora 2 (12s)",
}

# ── Fal.ai video ──────────────────────────────────────────────
FAL_VID_MODELS = {
    "fal-ai/kling-video/v1.6/standard/text-to-video": "Kling 1.6 نص←فيديو",
    "fal-ai/kling-video/v1.6/standard/image-to-video": "Kling 1.6 صورة←فيديو",
    "fal-ai/minimax-video/image-to-video":              "MiniMax صورة←فيديو",
    "fal-ai/ltx-video":                                 "LTX Video نص←فيديو",
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

    # ── اختيار الوضع ──────────────────────────────────────────
    if data in ("text_to_video", "image_to_video"):
        if not vip.is_vip(frm):
            tg.send_message(chat, "🔒 هذه الميزة للأعضاء VIP فقط.")
            return True
        mode = "text" if data == "text_to_video" else "image"
        _save_state(state_file, {"type": "video", "mode": mode, "step": "choose_provider"})
        _send_vid_provider_menu(tg, chat, mid, mode)
        return True

    # ── اختيار المزود ─────────────────────────────────────────
    if data and data.startswith("vid_provider|"):
        provider = data.split("|")[1]
        state.update({"provider": provider})
        mode = state.get("mode", "text")
        if provider == "original":
            state["step"] = "choose_orig_model"
            _save_state(state_file, state)
            _send_orig_vid_model_menu(tg, chat, mid, mode)
        else:
            state["step"] = "choose_fal_vid_model"
            _save_state(state_file, state)
            _send_fal_vid_model_menu(tg, chat, mid, mode)
        return True

    # ── النموذج الأصلي: اختيار موديل ─────────────────────────
    if data and data.startswith("vid_orig_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_ratio"})
        _save_state(state_file, state)
        _send_ratio_menu(tg, chat, mid)
        return True

    # ── Fal: اختيار موديل ─────────────────────────────────────
    if data and data.startswith("vid_fal_model|"):
        model = data.split("|")[1]
        mode  = state.get("mode", "text")
        state.update({"model": model})
        # نماذج صورة←فيديو تحتاج صورة أولاً
        if "image-to-video" in model or mode == "image":
            state["step"] = "awaiting_image"
        else:
            state["step"] = "choose_ratio"
        _save_state(state_file, state)
        if state["step"] == "choose_ratio":
            _send_ratio_menu(tg, chat, mid)
        else:
            md = FAL_VID_MODELS.get(model, model)
            tg.edit_caption(chat, mid,
                f"<b>الموديل:</b> {md}\n\n📸 <b>أرسل الصورة لتحويلها إلى فيديو:</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        return True

    # ── اختيار النسبة ─────────────────────────────────────────
    if data and data.startswith("vid_ratio|"):
        ratio = data.split("|")[1]
        mode  = state.get("mode", "text")
        state.update({"ratio": ratio})
        if mode == "text":
            state["step"] = "awaiting_text"
            _save_state(state_file, state)
            tg.edit_caption(chat, mid,
                f"<b>النسبة:</b> {ratio}\n\n✍️ <b>أرسل النص لإنشاء الفيديو:</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        else:
            state["step"] = "awaiting_image"
            _save_state(state_file, state)
            tg.edit_caption(chat, mid,
                f"<b>النسبة:</b> {ratio}\n\n📸 <b>أرسل الصورة لتحويلها إلى فيديو:</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        return True

    # ── استقبال صورة ──────────────────────────────────────────
    if state.get("step") == "awaiting_image" and state.get("type") == "video" and photo:
        fid  = photo[-1]["file_id"]
        link = tg.get_file(fid)
        if link:
            state.update({"image": link, "step": "awaiting_text_img_vid"})
            _save_state(state_file, state)
            tg.send_message(chat, "✅ <b>تم استلام الصورة!</b>\nالآن أرسل نصاً يصف الحركة:",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        return True

    # ── توليد الفيديو ─────────────────────────────────────────
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

        provider = cur.get("provider", "fal")
        if provider == "original" and VIDEO_API_URL:
            vid_url, err = _generate_orig_video(cur, text)
        else:
            vid_url, err = _generate_fal_video(cur, text)

        if stk_id:
            tg.delete_message(chat, stk_id)

        kb = Telegram.kb([[Telegram.btn("• رجوع •", "back")]])

        if vid_url:
            model = cur.get("model", "")
            md    = ORIG_MODELS.get(model, FAL_VID_MODELS.get(model, model))
            cap   = f"✅ <b>الموديل:</b> {md} | <b>النسبة:</b> {cur.get('ratio', '')}"
            tg.send_video(chat, vid_url, cap, {"reply_markup": kb})
        else:
            tg.send_message(chat, f"⚠️ <b>خطأ:</b>\n<code>{err[:200]}</code>", {"reply_markup": kb})

        db.unlock_user(frm)
        return True

    return False


# ── توليد بالنموذج الأصلي ─────────────────────────────────────
def _generate_orig_video(cur: dict, prompt: str):
    session_cookie = _init_video_session()
    params = {
        "action": "video",
        "p":      prompt,
        "m":      cur.get("model", "veo-3.1-lite"),
        "r":      cur.get("ratio", "16:9"),
    }
    if cur.get("image"):
        params["img"] = cur["image"]
    headers = {"User-Agent": "Mozilla/5.0"}
    if session_cookie:
        headers["Cookie"] = session_cookie
    try:
        resp   = requests.get(VIDEO_API_URL, params=params, headers=headers, timeout=180, verify=False)
        result = resp.json()
        if result.get("status") == "success" and result.get("video_url"):
            return result["video_url"], ""
        return None, result.get("message", resp.text[:200])
    except Exception as e:
        return None, str(e)


def _init_video_session() -> str:
    try:
        resp    = requests.get(VIDEO_API_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False)
        matches = re.findall(r'toNumbers\("([a-f0-9]+)"\)', resp.text)
        if len(matches) >= 3:
            key, iv, enc = bytes.fromhex(matches[0]), bytes.fromhex(matches[1]), bytes.fromhex(matches[2])
            cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            dec       = decryptor.update(enc) + decryptor.finalize()
            return f"__test={dec.hex()}"
    except Exception as e:
        logger.error("Video session: %s", e)
    return ""


# ── توليد بـ Fal.ai ───────────────────────────────────────────
def _generate_fal_video(cur: dict, prompt: str):
    model   = cur.get("model", "fal-ai/kling-video/v1.6/standard/text-to-video")
    payload = {"prompt": prompt}

    if cur.get("image"):
        payload["image_url"] = cur["image"]
    if cur.get("ratio"):
        payload["aspect_ratio"] = cur["ratio"]

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        resp   = requests.post(f"https://fal.run/{model}", json=payload, headers=headers, timeout=300)
        raw    = resp.text.strip()
        logger.error("FalVideo [%s]: %s", resp.status_code, raw[:300])
        result = resp.json()

        # استخراج رابط الفيديو
        for key in ("video", "video_url", "url", "output"):
            val = result.get(key)
            if isinstance(val, dict):
                val = val.get("url")
            if val:
                return val, ""

        videos = result.get("videos", [])
        if videos:
            return videos[0].get("url"), ""

        return None, raw
    except Exception as e:
        return None, str(e)


# ── القوائم ───────────────────────────────────────────────────
def _send_vid_provider_menu(tg: Telegram, chat: int, mid: int, mode: str) -> None:
    title = "🎬 نص ← فيديو" if mode == "text" else "🖼 صورة ← فيديو"
    rows  = [
        [Telegram.btn("🌟 النموذج الأصلي", "vid_provider|original")],
        [Telegram.btn("⚡ Fal.ai",          "vid_provider|fal")],
        [Telegram.btn("• رجوع •", "back")],
    ]
    tg.edit_caption(chat, mid, f"<b>{title}\n\n🎬 اختر مزود الفيديو:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_orig_vid_model_menu(tg: Telegram, chat: int, mid: int, mode: str) -> None:
    rows = [[Telegram.btn(v, f"vid_orig_model|{k}")] for k, v in ORIG_MODELS.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر الموديل:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_fal_vid_model_menu(tg: Telegram, chat: int, mid: int, mode: str) -> None:
    # فلترة حسب الوضع
    filtered = {k: v for k, v in FAL_VID_MODELS.items()
                if (mode == "text" and "text-to-video" in k or "ltx" in k)
                or (mode == "image" and "image-to-video" in k)
                or mode not in ("text", "image")}
    if not filtered:
        filtered = FAL_VID_MODELS
    rows = [[Telegram.btn(v, f"vid_fal_model|{k}")] for k, v in filtered.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر موديل Fal.ai:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    row  = [Telegram.btn(v, f"vid_ratio|{k}") for k, v in VID_RATIOS.items()]
    rows = [row, [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>📐 اختر نسبة الفيديو:</b>", {"reply_markup": Telegram.kb(rows)})


def _save_state(path: str, data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
