"""
================================================================
  handlers/image.py  —  Image creation & editing flow
================================================================
"""

import json
import os
import logging
import requests

from telegram import Telegram
from config import IMAGE_API_URL, LOADING_STICKER

logger = logging.getLogger(__name__)

IMG_MODELS = {
    "NanoBanana":    "NanaBanana",
    "NanoBanana2":   "NanaBanana 2",
    "NanoBananaPro": "NanaBanana Pro",
}

IMG_RATIOS = {
    "1:1": "1:1", "1:4": "1:4", "1:8": "1:8",
    "2:3": "2:3", "3:2": "3:2", "3:4": "3:4",
    "4:1": "4:1", "4:3": "4:3", "4:5": "4:5",
    "5:4": "5:4", "8:1": "8:1", "9:16": "9:16",
    "16:9": "16:9", "21:9": "21:9", "auto": "auto",
}

IMG_RES = {"1K": "1K", "2K": "2K", "4K": "4K"}


def handle_image(ctx: dict) -> bool:
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

    # ── Choose mode ───────────────────────────────────────────
    if data in ("create_image", "edit_image"):
        if not vip.is_vip(frm):
            tg.send_message(chat, "🔒 هذه الميزة للأعضاء VIP فقط.")
            return True
        mode = "create" if data == "create_image" else "edit"
        _save_state(state_file, {"mode": mode, "step": "choose_model", "type": "image"})
        _img_send_model_menu(tg, chat, mid)
        return True

    # ── Choose model ──────────────────────────────────────────
    if data and data.startswith("img_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_ratio"})
        _save_state(state_file, state)
        _img_send_ratio_menu(tg, chat, mid)
        return True

    # ── Choose ratio ──────────────────────────────────────────
    if data and data.startswith("img_ratio|"):
        ratio = data.split("|")[1]
        state.update({"ratio": ratio, "step": "choose_res"})
        _save_state(state_file, state)
        _img_send_res_menu(tg, chat, mid)
        return True

    # ── Choose resolution ─────────────────────────────────────
    if data and data.startswith("img_res|"):
        res  = data.split("|")[1]
        mode = state.get("mode", "create")
        state.update({"res": res})
        state["step"] = "awaiting_text" if mode == "create" else "awaiting_image"
        _save_state(state_file, state)
        md   = IMG_MODELS.get(state.get("model", ""), state.get("model", ""))
        hint = (
            "✍️ الآن أرسل النص لإنشاء الصورة"
            if mode == "create"
            else "📸 الآن أرسل الصورة التي تريد تعديلها"
        )
        tg.edit_caption(
            chat, mid,
            f"<b>الموديل:</b> {md}\n<b>النسبة:</b> {state['ratio']} | <b>الدقة:</b> {res}\n\n<b>{hint}</b>",
            {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
        )
        return True

    # ── Receive image for editing ─────────────────────────────
    if state.get("step") == "awaiting_image" and state.get("type") == "image" and photo:
        fid  = photo[-1]["file_id"]
        link = tg.get_file(fid)
        if link:
            state.update({"image": link, "step": "awaiting_text_edit"})
            _save_state(state_file, state)
            tg.send_message(
                chat,
                "✅ <b>تم استلام الصورة! الآن أرسل نص التعديل.</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
            )
        return True

    # ── Receive text → generate image ────────────────────────
    step = state.get("step", "")
    typ  = state.get("type", "")
    if typ == "image" and step in ("awaiting_text", "awaiting_text_edit") and text and text != "/start":
        if not db.is_user_free(frm):
            return True
        db.lock_user(frm)
        cur = dict(state)
        if os.path.exists(state_file):
            os.remove(state_file)

        stk    = tg.send_sticker(chat, LOADING_STICKER)
        stk_id = stk.get("result", {}).get("message_id")

        model     = cur.get("model", "NanoBanana2")
        api_model = "NanoBanana2" if model == "NanoBananaPro" else model

        payload = {
            "text":  text,
            "model": api_model,
            "ratio": cur.get("ratio", "1:1"),
            "res":   cur.get("res",   "1K"),
            "links": cur.get("image", ""),
        }

        # ── استدعاء الـ API وتسجيل الرد الكامل ──────────────
        raw_text = ""
        result   = None
        try:
            resp     = requests.post(
                IMAGE_API_URL, data=payload, timeout=120, verify=False
            )
            raw_text = resp.text.strip()
            # سجّل الرد دائماً حتى نعرف الشكل الحقيقي
            logger.error("Image API [%s] response: %s", resp.status_code, raw_text[:500])
            try:
                result = resp.json()
            except Exception:
                result = None
        except Exception as e:
            logger.error("Image API connection error: %s", e)
            raw_text = str(e)

        if stk_id:
            tg.delete_message(chat, stk_id)

        kb = Telegram.kb([[Telegram.btn("• رجوع •", "back")]])

        # ── فحص شامل للـ url في الـ response ────────────────
        img_url = None
        if result and isinstance(result, dict):
            # جرّب كل المفاتيح المحتملة
            for key in ("url", "image", "image_url", "link", "result", "output"):
                if result.get(key):
                    img_url = result[key]
                    break

        if img_url:
            md        = IMG_MODELS.get(cur.get("model", ""), cur.get("model", ""))
            res_label = (result or {}).get("resolution", cur.get("res"))
            cap       = f"<b>✅ الموديل:</b> {md}\n<b>النسبة:</b> {cur.get('ratio')} | <b>الدقة:</b> {res_label}"
            tg.send_photo(chat, img_url, cap, {"has_spoiler": "true", "reply_markup": kb})
        else:
            # أظهر السبب الحقيقي للخطأ
            err = raw_text[:300] if raw_text else "لا يوجد رد من الخادم"
            tg.send_message(
                chat,
                f"⚠️ <b>خطأ من الـ API:</b>\n<code>{err}</code>",
                {"reply_markup": kb},
            )

        db.unlock_user(frm)
        return True

    return False


# ── Menu helpers ──────────────────────────────────────────────
def _img_send_model_menu(tg: Telegram, chat: int, mid: int) -> None:
    keys = list(IMG_MODELS.keys())
    rows = []
    for i in range(0, len(keys), 2):
        row = [Telegram.btn(IMG_MODELS[keys[i]], f"img_model|{keys[i]}")]
        if i + 1 < len(keys):
            row.append(Telegram.btn(IMG_MODELS[keys[i + 1]], f"img_model|{keys[i + 1]}"))
        rows.append(row)
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر الموديل:</b>", {"reply_markup": Telegram.kb(rows)})


def _img_send_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    keys = list(IMG_RATIOS.keys())
    rows = []
    for i in range(0, len(keys), 3):
        row = []
        for j in range(3):
            if i + j < len(keys):
                v = keys[i + j]
                row.append(Telegram.btn(IMG_RATIOS[v], f"img_ratio|{v}"))
        rows.append(row)
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>📐 اختر النسبة:</b>", {"reply_markup": Telegram.kb(rows)})


def _img_send_res_menu(tg: Telegram, chat: int, mid: int) -> None:
    row  = [Telegram.btn(v, f"img_res|{k}") for k, v in IMG_RES.items()]
    rows = [row, [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>🔍 اختر الدقة:</b>", {"reply_markup": Telegram.kb(rows)})


def _save_state(path: str, data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
