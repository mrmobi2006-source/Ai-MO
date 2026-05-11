"""
================================================================
  telegram.py  —  Telegram Bot API wrapper
================================================================
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)


class Telegram:
    def __init__(self, token: str):
        self.token   = token
        self.base    = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        self.session.verify = False  # تجاهل SSL مثل PHP الأصلي

    # ── Generic call ─────────────────────────────────────────
    def call(self, method: str, data: dict = None) -> dict:
        url  = f"{self.base}/{method}"
        data = data or {}
        try:
            resp = self.session.post(url, data=data, timeout=30)
            return resp.json()
        except Exception as e:
            logger.error("Telegram.call %s: %s", method, e)
            return {}

    # ── Helpers ───────────────────────────────────────────────
    def send_message(self, chat: int, text: str, extra: dict = None) -> dict:
        payload = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
        if extra:
            payload.update(extra)
        return self.call("sendMessage", payload)

    def send_photo(self, chat: int, photo: str, caption: str = "", extra: dict = None) -> dict:
        payload = {
            "chat_id":    chat,
            "photo":      photo,
            "caption":    caption,
            "parse_mode": "HTML",
        }
        if extra:
            payload.update(extra)
        return self.call("sendPhoto", payload)

    def send_video(self, chat: int, video: str, caption: str = "", extra: dict = None) -> dict:
        payload = {
            "chat_id":    chat,
            "video":      video,
            "caption":    caption,
            "parse_mode": "HTML",
        }
        if extra:
            payload.update(extra)
        return self.call("sendVideo", payload)

    def edit_caption(self, chat: int, mid: int, caption: str, extra: dict = None) -> dict:
        payload = {
            "chat_id":    chat,
            "message_id": mid,
            "caption":    caption,
            "parse_mode": "HTML",
        }
        if extra:
            payload.update(extra)
        return self.call("editMessageCaption", payload)

    def edit_text(self, chat: int, mid: int, text: str, extra: dict = None) -> dict:
        payload = {
            "chat_id":    chat,
            "message_id": mid,
            "text":       text,
            "parse_mode": "HTML",
        }
        if extra:
            payload.update(extra)
        return self.call("editMessageText", payload)

    def delete_message(self, chat: int, mid: int) -> None:
        self.call("deleteMessage", {"chat_id": chat, "message_id": mid})

    def send_sticker(self, chat: int, sticker: str) -> dict:
        return self.call("sendSticker", {"chat_id": chat, "sticker": sticker})

    def get_file(self, file_id: str) -> str | None:
        res = self.call("getFile", {"file_id": file_id})
        if res.get("ok"):
            path = res["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{self.token}/{path}"
        return None

    def set_webhook(self, url: str) -> dict:
        return self.call("setWebhook", {"url": url})

    # ── Keyboard helpers ──────────────────────────────────────
    @staticmethod
    def kb(rows: list) -> str:
        return json.dumps({"inline_keyboard": rows})

    @staticmethod
    def btn(text: str, data: str) -> dict:
        return {"text": text, "callback_data": data}
