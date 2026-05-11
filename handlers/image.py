"""
================================================================
  handlers/image.py  —  Image creation & editing
  يجرب IMAGE_API_URL الأصلي أولاً، ثم Fal.ai كبديل
================================================================
"""

import json
import os
import logging
import requests

from telegram import Telegram
from config import FAL_API_KEY, IMAGE_API_URL, LOADING_STICKER

logger = logging.getLogger(__name__)

# ── Fal.ai ────────────────────────────────────────────────────
FAL_ENDPOINTS = {
    "flux-dev":     "fal-ai/flux/dev",
    "flux-schnell": "fal-ai/flux/schnell",
    "flux-pro":     "fal-ai/flux-pro",
}

FAL_MODELS = {
    "flux-dev":     "Flux Dev",
    "flux-schnell": "Flux Schnell (سريع)",
    "flux-pro":     "Flux Pro",
}

FAL_RATIOS = {
    "square":         "1:1",
    "square_hd":      "1:1 HD",
    "portrait_4_3":   "3:4",
    "portrait_16_9":  "9:16",
    "landscape_4_3":  "4:3",
    "landscape_16_9": "16:9",
}

FAL_QUALITY = {"1": "سريع", "2": "متوازن", "4": "عالي"}

# ── النموذج الأصلي ────────────────────────────────────────────
ORIG_MODELS = {
    "NanoBanana":    "NanaBanana",
    "NanoBanana2":   "NanaBanana 2",
    "NanoBananaPro": "NanaBanana Pro",
}

ORIG_RATIOS = {
    "1:1": "1:1", "9:16": "9:16", "16:9": "16:9",
    "2:3": "2:3", "3:2": "3:2", "4:3": "4:3", "auto": "auto",
}

ORIG_RES = {"1K": "1K", "2K": "2K", "4K": "4K"}


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
        _save_state(state_file, {"mode": mode, "step": "choose_provider", "type": "image"})
        _send_provider_menu(tg, chat, mid)
        return True

    # ── اختيار المزود ─────────────────────────────────────────
    if data and data.startswith("img_provider|"):
        provider = data.split("|")[1]
        state.update({"provider": provider})
        _save_state(state_file, state)
        if provider == "original":
            state["step"] = "choose_orig_model"
            _save_state(state_file, state)
            _send_orig_model_menu(tg, chat, mid)
        else:
            state["step"] = "choose_fal_model"
            _save_state(state_file, state)
            _send_fal_model_menu(tg, chat, mid)
        return True

    # ── النموذج الأصلي: اختيار موديل ─────────────────────────
    if data and data.startswith("img_orig_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_orig_ratio"})
        _save_state(state_file, state)
        _send_orig_ratio_menu(tg, chat, mid)
        return True

    # ── النموذج الأصلي: اختيار نسبة ──────────────────────────
    if data and data.startswith("img_orig_ratio|"):
        ratio = data.split("|")[1]
        state.update({"ratio": ratio, "step": "choose_orig_res"})
        _save_state(state_file, state)
        _send_orig_res_menu(tg, chat, mid)
        return True

    # ── النموذج الأصلي: اختيار دقة ───────────────────────────
    if data and data.startswith("img_orig_res|"):
        res  = data.split("|")[1]
        mode = state.get("mode", "create")
        state.update({"res": res, "step": "awaiting_text" if mode == "create" else "awaiting_image"})
        _save_state(state_file, state)
        md   = ORIG_MODELS.get(state.get("model", ""), state.get("model", ""))
        hint = "✍️ أرسل النص لإنشاء الصورة" if mode == "create" else "📸 أرسل الصورة للتعديل"
        tg.edit_caption(chat, mid,
            f"<b>الموديل:</b> {md} | <b>النسبة:</b> {state.get('ratio')} | <b>الدقة:</b> {res}\n\n<b>{hint}</b>",
            {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        return True

    # ── Fal.ai: اختيار موديل ──────────────────────────────────
    if data and data.startswith("img_fal_model|"):
        model = data.split("|")[1]
        state.update({"model": model, "step": "choose_fal_ratio"})
        _save_state(state_file, state)
        _send_fal_ratio_menu(tg, chat, mid)
        return True

    # ── Fal.ai: اختيار نسبة ───────────────────────────────────
    if data and data.startswith("img_fal_ratio|"):
        ratio = data.split("|")[1]
        state.update({"ratio": ratio, "step": "choose_fal_quality"})
        _save_state(state_file, state)
        _send_fal_quality_menu(tg, chat, mid)
        return True

    # ── Fal.ai: اختيار جودة ───────────────────────────────────
    if data and data.startswith("img_fal_quality|"):
        quality = data.split("|")[1]
        mode    = state.get("mode", "create")
        state.update({"quality": quality, "step": "awaiting_text" if mode == "create" else "awaiting_image"})
        _save_state(state_file, state)
        md   = FAL_MODELS.get(state.get("model", ""), state.get("model", ""))
        hint = "✍️ أرسل النص لإنشاء الصورة" if mode == "create" else "📸 أرسل الصورة للتعديل"
        tg.edit_caption(chat, mid,
            f"<b>الموديل:</b> {md} | <b>النسبة:</b> {FAL_RATIOS.get(ratio, ratio)} | <b>الجودة:</b> {FAL_QUALITY.get(quality)}\n\n<b>{hint}</b>",
            {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
        return True

    # ── استقبال صورة للتعديل ──────────────────────────────────
    if state.get("step") == "awaiting_image" and state.get("type") == "image" and photo:
        fid  = photo[-1]["file_id"]
        link = tg.get_file(fid)
        if link:
            state.update({"image": link, "step": "awaiting_text_edit"})
            _save_state(state_file, state)
            tg.send_message(chat, "✅ <b>تم استلام الصورة! الآن أرسل نص التعديل.</b>",
                {"reply_markup": Telegram.kb([[Telegram.btn("• رجوع •", "back")]])})
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

        provider = cur.get("provider", "fal")
        if provider == "original" and IMAGE_API_URL:
            img_url, err = _generate_original(cur, text)
        else:
            img_url, err = _generate_fal(cur, text)

        if stk_id:
            tg.delete_message(chat, stk_id)

        kb = Telegram.kb([[Telegram.btn("• رجوع •", "back")]])

        if img_url:
            model = cur.get("model", "")
            md    = ORIG_MODELS.get(model, FAL_MODELS.get(model, model))
            cap   = f"✅ <b>الموديل:</b> {md}"
            tg.send_photo(chat, img_url, cap, {"has_spoiler": "true", "reply_markup": kb})
        else:
            tg.send_message(chat, f"⚠️ <b>خطأ:</b>\n<code>{err[:200]}</code>", {"reply_markup": kb})

        db.unlock_user(frm)
        return True

    return False


# ── توليد بالنموذج الأصلي ─────────────────────────────────────
def _generate_original(cur: dict, text: str):
    model     = cur.get("model", "NanoBanana2")
    api_model = "NanoBanana2" if model == "NanoBananaPro" else model
    payload   = {
        "text":  text,
        "model": api_model,
        "ratio": cur.get("ratio", "1:1"),
        "res":   cur.get("res",   "1K"),
        "links": cur.get("image", ""),
    }
    try:
        resp     = requests.post(IMAGE_API_URL, data=payload, timeout=120, verify=False)
        raw      = resp.text.strip()
        logger.error("OrigAPI [%s]: %s", resp.status_code, raw[:300])
        result   = resp.json()
        for key in ("url", "image", "image_url", "link"):
            if result.get(key):
                return result[key], ""
        return None, raw
    except Exception as e:
        return None, str(e)


# ── توليد بـ Fal.ai ───────────────────────────────────────────
def _generate_fal(cur: dict, text: str):
    model    = cur.get("model", "flux-dev")
    endpoint = FAL_ENDPOINTS.get(model, "fal-ai/flux/dev")
    payload  = {
        "prompt":               text,
        "image_size":           cur.get("ratio", "square"),
        "num_images":           1,
        "num_inference_steps":  int(cur.get("quality", "2")),
    }
    if cur.get("image"):
        payload["image_url"] = cur["image"]

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        resp   = requests.post(f"https://fal.run/{endpoint}", json=payload, headers=headers, timeout=120)
        raw    = resp.text.strip()
        logger.error("FalAPI [%s]: %s", resp.status_code, raw[:300])
        result = resp.json()
        images = result.get("images", [])
        if images:
            return images[0].get("url"), ""
        for key in ("url", "image", "image_url"):
            if result.get(key):
                return result[key], ""
        return None, raw
    except Exception as e:
        return None, str(e)


# ── القوائم ───────────────────────────────────────────────────
def _send_provider_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [
        [Telegram.btn("🌟 NanaBanana (الأصلي)", "img_provider|original")],
        [Telegram.btn("⚡ Fal.ai - Flux",        "img_provider|fal")],
        [Telegram.btn("• رجوع •", "back")],
    ]
    tg.edit_caption(chat, mid, "<b>🖼 اختر مزود الصور:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_orig_model_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [[Telegram.btn(v, f"img_orig_model|{k}")] for k, v in ORIG_MODELS.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر الموديل:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_orig_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    keys = list(ORIG_RATIOS.keys())
    rows = []
    for i in range(0, len(keys), 3):
        row = [Telegram.btn(ORIG_RATIOS[keys[i+j]], f"img_orig_ratio|{keys[i+j]}")
               for j in range(3) if i+j < len(keys)]
        rows.append(row)
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>📐 اختر النسبة:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_orig_res_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [[Telegram.btn(v, f"img_orig_res|{k}") for k, v in ORIG_RES.items()],
            [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>🔍 اختر الدقة:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_fal_model_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [[Telegram.btn(v, f"img_fal_model|{k}")] for k, v in FAL_MODELS.items()]
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>🤖 اختر موديل Flux:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_fal_ratio_menu(tg: Telegram, chat: int, mid: int) -> None:
    keys = list(FAL_RATIOS.keys())
    rows = []
    for i in range(0, len(keys), 3):
        row = [Telegram.btn(FAL_RATIOS[keys[i+j]], f"img_fal_ratio|{keys[i+j]}")
               for j in range(3) if i+j < len(keys)]
        rows.append(row)
    rows.append([Telegram.btn("• رجوع •", "back")])
    tg.edit_caption(chat, mid, "<b>📐 اختر النسبة:</b>", {"reply_markup": Telegram.kb(rows)})


def _send_fal_quality_menu(tg: Telegram, chat: int, mid: int) -> None:
    rows = [[Telegram.btn(v, f"img_fal_quality|{k}") for k, v in FAL_QUALITY.items()],
            [Telegram.btn("• رجوع •", "back")]]
    tg.edit_caption(chat, mid, "<b>✨ اختر الجودة:</b>", {"reply_markup": Telegram.kb(rows)})


def _save_state(path: str, data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
