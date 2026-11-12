# 🚀 Telegram AI Botini Render.com da 24/7 Bepul Ishga Tushirish Qo'llanmasi

Ushbu qo'llanma orqali botingizni **Render.com** bulutli serveriga joylab, kompyuteringiz o'chiq bo'lsa ham **24 soat / 7 kun uzluksiz** bepul ishlaydigan qilasiz.

---

## 1-QADAM: Render.com da ro'yxatdan o'tish

1. [Render.com](https://render.com/) saytiga kiring.
2. **GitHub** akkauntingiz orqali tizimga kiring (**Sign up with GitHub**).

---

## 2-QADAM: Yangi Web Service yaratish

1. Render panelida yuqoridagi **«New +»** tugmasini bosing va **«Web Service»** ni tanlang.
2. **«Build and deploy from a Git repository»** ni tanlab, **«Next»** bosing.
3. GitHub repozitoriyangizni (`miuceo/telehgram-chatbot`) topib, yonidagi **«Connect»** tugmasini bosing.
4. Quyidagi sozlamalarni to'ldiring:
   * **Name:** `telegram-chatbot` (yoki istalgan nom)
   * **Region:** `Frankfurt (EU Central)` yoki `Singapore`
   * **Branch:** `main`
   * **Root Directory:** (bo'sh qoldiring)
   * **Runtime:** `Python 3`
   * **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   * **Start Command:**
     ```bash
     python bot.py
     ```
   * **Instance Type:** **Free** (0$ / month)

---

## 3-QADAM: Maxfiy kalitlarni kiritish (Environment Variables)

Pastga tushib, **«Environment Variables»** (yoki **«Advanced» -> «Add Environment Variable»**) bo'limiga quyidagi kalitlarni qo'shing:

| Key (Nomi) | Value (Qiymati) |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | *Sizning Telegram Bot Tokeningiz* |
| `GEMINI_API_KEY` | *Sizning Google AI Studio kalitingiz* |
| `BRAIN_MODEL` | `gemma-4-26b-a4b-it` |
| `BRAIN_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |
| `VISION_MODEL` | `gemma-4-31b-it` |
| `VISION_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |
| `WRITER_MODEL` | `gemma-4-31b-it` |
| `WRITER_FALLBACK_MODEL` | `gemma-4-26b-a4b-it` |
| `TRANSCRIBE_MODEL` | `gemini-3.5-transcribe` |
| `TRANSCRIBE_FALLBACK_MODEL` | `gemini-3.1-flash-lite` |
| `LONG_AUDIO_MODEL` | `gemini-3.1-flash-lite` |
| `LONG_AUDIO_FALLBACK_MODEL` | `gemini-3.5-flash-lite` |

Sahifaning eng pastidagi **«Deploy Web Service»** tugmasini bosing!
Render o'zi 1-2 daqiqada kutubxonalarni o'rnatib, botingizni ishga tushiradi. Jurnalda `Application started` yozuvi chiqsa — bot serverda to'liq ishga tushgan bo'ladi!

---

## 4-QADAM: 24/7 Uxlab qolmasligini ta'minlash (Muhim!)

Render'ning bepul tarifi 15 daqiqa davomida so'rov kelmasa serverni vaqtincha "uyqu"ga qo'yadi. Buni oldini olish va 24/7 faol ushlab turish uchun:

1. Render panelida botingizning yuqorisida berilgan bepul havolasini nusxalang (masalan: `https://telegram-chatbot-xxxx.onrender.com`).
2. [cron-job.org](https://cron-job.org/) yoki [uptimerobot.com](https://uptimerobot.com/) saytiga bepul kiring.
3. Yangi monitor / cronjob yarating:
   * **URL:** Render bergan havolangiz (`https://telegram-chatbot-xxxx.onrender.com`)
   * **Interval:** Har **10 daqiqada** (Every 10 minutes)
4. Saqlang! Endi bu xizmat har 10 daqiqada Render'dagi botingizga signal yuborib turadi va server hech qachon uxlamay, **24/7 uzluksiz** ishlaydi!
