"""
================================================================
  handlers/image.py  —  Image creation & editing (Fal.ai)
================================================================
"""

import json
import os
import logging
import requests

from telegram import Telegram
from config import FAL_API_KEY, LOADING_STICKER

logger = logging.getLogger(__name__)

FAL_URL = "https://fal.run/fal-ai/flux/dev"

IMG_MODELS = {
    "flux-dev":     "Flux Dev",
    "flux-schnell": "Flux Schnell (سريع)",
    "flux-pro":     "Flux Pro",
}

IMG_RATIOS = {
    "square":           "1:1",
    "square_hd":        "1:1 HD",
    "portrait_4_3":     "3:4",
    "portrait_16_9":    "9:16",
    "landscape_4_3":    "4:3",
    "landscape_16_9":   "16:9",
}

IMG_QUALITY = {"1": "سريع (1)", "2": "متوازن (2)", "4": "جودة عالية (4)"}

FAL_ENDPOINTS = {
    "flux-dev":     "fal-ai/flux/dev",
    "flux-schnell": "fal-ai/flux/schnell",
    "flux-pro":     "fal-ai/flux-pro",
}


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

    # ── اختيار الوضع ──────────────────────────────────────────
    if data in ("create_image", "edit_image"):
        if not vip.is_vip(frm):
            tg.send_message(chat, "🔒 هذه الميزة للأعضاء VIP فقط.")
            return True
        mode = "create" if data == "create_image" else "edit"
        _save_state(state_file, {"mode": mode, "step": "choose_model", "type": "image"})
        _send_model_menu(tg, chat, mid)
        return True

    # ── اختيار الموديل ────────────────────────────────────────
    if data and data.startswith("img_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_ratio"})
        _save_state(state_file, state)
        _send_ratio_menu(tg, chat, mid)
        return True

    # ── اختيار النسبة ─────────────────────────────────────────
    if data and data.startswith("img_ratio|"):
        ratio = data.split("|")[1]
        state.update({"ratio": ratio, "step": "choose_quality"})
        _save_state(state_file, state)
        _send_quality_menu(tg, chat, mid)
        return True

    # ── اختيار الجودة ─────────────────────────────────────────
    if data and data.startswith("img_quality|"):
        quality = data.split("|")[1]
        mode    = state.get("mode", "create")
        state.update({"quality": quality})
        state["step"] = "awaiting_text" if mode == "create" else "awaiting_image"
        _save_state(state_file, state)
        md   = IMG_MODELS.get(state.get("model", ""), state.get("model", ""))
        hint = "✍️ الآن أرسل النص لإنشاء الصورة" if mode == "create" else "📸 الآن أرسل الصورة التي تريد تعديلها"
        tg.edit_caption(
            chat, mid,
            f"<b>الموديل:</b> {md}\n<b>النسبة:</b> {IMG_RATIOS.get(ratio, ratio)} | <b>الجودة:</b> {IMG_QUALITY.get(quality, quality)}\n\n<b>{hint}</b>",
            {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])},
        )
        return True

    # ── استقبال صورة للتعديل ──────────────────────────────────
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

    # ── توليد الصورة ──────────────────────────────────────────
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

        model    = cur.get("model", "flux-dev")
        endpoint = FAL_ENDPOINTS.get(model, "fal-ai/flux/dev")
        url      = f"https://fal.run/{endpoint}"

        payload = {
            "prompt":      text,
            "image_size":  cur.get("ratio", "square"),
            "num_images":  1,
            "num_inference_steps": int(cur.get("quality", "2")),
        }
        # للتعديل: أضف صورة المرجع
        if cur.get("image"):
            payload["image_url"] = cur["image"]

        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type":  "application/json",
        }

        raw_text = ""
        result   = None
        try:
            resp     = requests.post(url, json=payload, headers=headers, timeout=120)
            raw_text = resp.text.strip()
            logger.error("Fal API [%s]: %s", resp.status_code, raw_text[:300])
            result   = resp.json()
        except Exception as e:
            logger.error("Fal API error: %s", e)
            raw_text = str(e)

        if stk_id:
            tg.delete_message(chat, stk_id)

        kb = Telegram.kb([[Telegram.btn("• رجوع •", "back")]])

        # استخراج رابط الصورة
        img_url = None
        if result and isinstance(result, dict):
            images = result.get("images", [])
            if images:
                img_url = images[0].get("url")
            if not img_url:
                for key in ("url", "image", "image_url", "output"):
                    if result.get(key):
                        img_url = result[key]
                        break

        if img_url:
            md  = IMG_MODELS.get(model, model)
            rat = IMG_RATIOS.get(cur.get("ratio", ""), cur.get("ratio", ""))
            cap = f"✅ <b>الموديل:</b> {md} | <b>النسبة:</b> {rat}"
            tg.send_photo(chat, img_url, cap, {"has_spoiler": "true", "reply_markup": kb})
        else:
            err = raw_text[:300] if raw_text else "لا يوجد رد"
            tg.send_message(chat, f"⚠️ <b>خطأ:</b>\n<code>{err}</code>", {"reply_markup": kb})

        db.unlock_user(frm)
        return True

    return False


# ── قوائم الاختيار ────────────────────────────────────────────
def _send_model_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [[Telegram.btn(v, f"img_model|{k}")] for k, v in IMG_MODELS.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر الموديل:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    keys = list(IMG_RATIOS.keys())
    rows = []
    for i in range(0, len(keys), 3):
        row = []
        for j in range(3):
            if i + j < len(keys):
                k = keys[i + j]
                row.append(Telegram.btn(IMG_RATIOS[k], f"img_ratio|{k}"))
        rows.append(row)
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>📐 اختر النسبة:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_quality_menu(tg: Telegram, chat: int, mid: int) -> None:
    row  = [Telegram.btn(v, f"img_quality|{k}") for k, v in IMG_QUALITY.items()]
    rows = [row, [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>✨ اختر الجودة:</b>", {"reply_markup": Telegram.kb(rows)})


def _save_state(path: str, data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
