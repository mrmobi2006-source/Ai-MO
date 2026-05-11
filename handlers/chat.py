"""
================================================================
  handlers/chat.py  —  AI Chat via Groq (LLaMA 3.1)
================================================================
"""

import logging
import requests

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "أنت مساعد ذكي اسمك NanaBanana 🍌. "
    "تتحدث العربية بشكل طبيعي وودي. "
    "أجوبتك مختصرة ومفيدة. "
    "إذا سألك أحد عن هويتك قل أنك NanaBanana، مساعد ذكي."
)


def handle_chat(ctx: dict) -> bool:
    tg   = ctx["tg"]
    vip  = ctx["vip"]
    chat = ctx["chat"]
    frm  = ctx["frm"]
    text = ctx["text"]
    data = ctx["data"]

    # زر المحادثة من القائمة
    if data == "ai_chat":
        if not vip.is_vip(frm):
            tg.send_message(chat, "🔒 هذه الميزة للأعضاء VIP فقط.")
            return True
        tg.send_message(
            chat,
            "🤖 <b>وضع المحادثة الذكية</b>\n\nأرسل أي سؤال أو كلام وسأرد عليك!\nللخروج اضغط /start",
            {"reply_markup": tg.kb([[tg.btn("• رجوع •", "back")]])}
        )
        return True

    # أي نص عادي (ليس أمر) → رد بالـ AI
    if text and not text.startswith("/") and vip.is_vip(frm):
        reply = _ask_groq(text)
        if reply:
            tg.send_message(chat, reply, {
                "reply_markup": tg.kb([[tg.btn("• رجوع •", "back")]])
            })
            return True

    return False


def _ask_groq(user_msg: str) -> str | None:
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        return "⚠️ لم يتم ضبط مفتاح Groq API."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_msg},
        ],
        "max_tokens":  1024,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(GROQ_URL, json=body, headers=headers, timeout=30)
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error("Groq API error: %s", e)
        return "⚠️ حدث خطأ في الاتصال بالذكاء الاصطناعي، حاول مجدداً."
