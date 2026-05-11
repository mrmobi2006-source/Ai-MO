"""
================================================================
  config.py  —  اقرأ الإعدادات من متغيرات البيئة
================================================================
"""

import os

BOT_TOKEN       = os.environ.get("BOT_TOKEN",       "")
BOT_USERNAME    = os.environ.get("BOT_USERNAME",    "")
ADMIN_ID        = int(os.environ.get("ADMIN_ID",    "0"))
WELCOME_PHOTO   = os.environ.get("WELCOME_PHOTO",   "https://t.me/Z_O_Z_0o0/36")
LOADING_STICKER = os.environ.get("LOADING_STICKER", "CAACAgIAAxkBAAERGrpp6qpwhZeU1z7ksy3kgUrtPadzwAACQgEAAs0bMAgEAoCtK287vjsE")
IMAGE_API_URL   = os.environ.get("IMAGE_API_URL",   "")
VIDEO_API_URL   = os.environ.get("VIDEO_API_URL",   "")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY",    "")
