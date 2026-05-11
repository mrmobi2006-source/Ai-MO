# 🍌 NanaBanana VIP Bot (Python)

بوت تيليغرام VIP كامل لتوليد الصور والفيديو بالذكاء الاصطناعي — مُحوَّل من PHP إلى Python.

## ✨ الميزات
- 🖼 **إنشاء صورة** من نص
- ✏️ **تعديل صورة** بنص
- 🎬 **نص ← فيديو** (Veo 3.1 / Sora 2)
- 🖼 **صورة ← فيديو**
- ⭐ **نظام VIP كامل** مع إدارة المشرفين

---

## 🚀 خطوات الرفع

### 1️⃣ رفع الكود على GitHub

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nana-bot.git
git push -u origin main
```

> ⚠️ **config.py مضاف في .gitignore** — لن يُرفع على GitHub.
> ستضع الإعدادات عبر Environment Variables في Railway.

---

### 2️⃣ الرفع على Railway

1. سجّل دخول على [railway.app](https://railway.app)
2. اضغط **New Project → Deploy from GitHub Repo**
3. اختر الريبو
4. اذهب إلى **Variables** وأضف المتغيرات التالية:

| المتغير | القيمة |
|---------|--------|
| `BOT_TOKEN` | توكن البوت من BotFather |
| `BOT_USERNAME` | اسم البوت (بدون @) |
| `ADMIN_ID` | آيدي التيليغرام الخاص بك |
| `WELCOME_PHOTO` | رابط صورة الترحيب (اختياري) |
| `LOADING_STICKER` | file_id الستيكر (اختياري) |
| `IMAGE_API_URL` | رابط API الصور (اختياري) |
| `VIDEO_API_URL` | رابط API الفيديو (اختياري) |

5. بعد الـ deploy، انسخ الرابط من **Settings → Domains**
6. فعّل الويب هوك:

```bash
python setup.py set https://YOUR-APP.railway.app
```

أو محلياً بعد ضبط المتغيرات:

```bash
BOT_TOKEN=xxx python setup.py set https://YOUR-APP.railway.app
```

---

## ⚙️ أوامر الأدمن

| الأمر | الوظيفة |
|-------|---------|
| `/vip_add 123456789 7d` | منح VIP لشخص لمدة 7 أيام |
| `/vip_add 123456789 24h` | منح VIP لمدة 24 ساعة |
| `/vip_add 123456789 60m` | منح VIP لمدة 60 دقيقة |
| `/vip_remove 123456789` | إلغاء VIP لشخص |
| `/vip_all 48h` | تفعيل VIP للجميع |
| `/vip_all_remove` | إلغاء VIP للجميع |
| `/vip_status 123456789` | حالة مستخدم |
| `/admin_add 123456789` | إضافة مشرف |
| `/admin_remove 123456789` | حذف مشرف |
| `/admin_list` | قائمة المشرفين |
| `/help_admin` | مساعدة مختصرة |

**صيغ المدة:** `7d` = أيام | `24h` = ساعات | `60m` = دقائق

---

## 📁 هيكل الملفات

```
├── bot.py               # الملف الرئيسي (Flask webhook)
├── config.py            # الإعدادات من متغيرات البيئة
├── database.py          # قاعدة البيانات SQLite
├── telegram.py          # مكتبة Telegram API
├── vip.py               # نظام VIP والأدمن
├── handlers/
│   ├── __init__.py
│   ├── start.py         # شاشة البداية
│   ├── image.py         # إنشاء وتعديل الصور
│   ├── video.py         # توليد الفيديو
│   └── admin.py         # أوامر الأدمن
├── setup.py             # إعداد الويب هوك
├── requirements.txt     # المكتبات المطلوبة
├── railway.json         # إعدادات Railway
├── nixpacks.toml        # بناء Python على Railway
├── Procfile             # أمر التشغيل
└── .gitignore
```

---

## 🔧 تشغيل محلي للاختبار

```bash
pip install -r requirements.txt

export BOT_TOKEN="توكن_البوت"
export ADMIN_ID="123456789"
export BOT_USERNAME="اسم_البوت"

python bot.py
# يشتغل على http://localhost:8080
```
