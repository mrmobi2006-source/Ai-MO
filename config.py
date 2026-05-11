"""
================================================================
  config.py  —  اقرأ الإعدادات من متغيرات البيئة
  على Railway أضف هذه المتغيرات في قسم Variables.
================================================================
"""

import os

BOT_TOKEN        = os.environ.get("BOT_TOKEN",        "YOUR_BOT_TOKEN_HERE")
BOT_USERNAME     = os.environ.get("BOT_USERNAME",     "YOUR_BOT_USERNAME")
ADMIN_ID         = int(os.environ.get("ADMIN_ID",     "123456789"))
WELCOME_PHOTO    = os.environ.get("WELCOME_PHOTO",    "https://t.me/Z_O_Z_0o0/36")
LOADING_STICKER  = os.environ.get("LOADING_STICKER",  "CAACAgIAAxkBAAERGrpp6qpwhZeU1z7ksy3kgUrtPadzwAACQgEAAs0bMAgEAoCtK287vjsE")
IMAGE_API_URL    = os.environ.get("IMAGE_API_URL",    "https://zecora0.serv00.net/ai/NanaBanana.php")
VIDEO_API_URL    = os.environ.get("VIDEO_API_URL",    "https://devil.kesug.com/system/video.php")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
