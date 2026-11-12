import os
from pathlib import Path
from dotenv import load_dotenv

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Asosiy sozlamalar
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# ==========================================
# SUN'IY INTELLEKT MODELLARI (100% BEPUL)
# ==========================================
# 1. Agent miyasi (funksiyalar va marshrutlash)
BRAIN_MODEL = os.getenv("BRAIN_MODEL", "gemma-4-26b-a4b-it").strip()
BRAIN_FALLBACK_MODEL = os.getenv("BRAIN_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()

# 2. Rasmlarni tushunish va tahlil qilish
VISION_MODEL = os.getenv("VISION_MODEL", "gemma-4-31b-it").strip()
VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()

# 3. Matnlar: suhbat, xulosa, tarjima, test tuzish
WRITER_MODEL = os.getenv("WRITER_MODEL", "gemma-4-31b-it").strip()
WRITER_FALLBACK_MODEL = os.getenv("WRITER_FALLBACK_MODEL", "gemma-4-26b-a4b-it").strip()

# 4. Qisqa audio (<= 55 daqiqa) transkripsiyasi
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gemini-3.5-transcribe").strip()
TRANSCRIBE_FALLBACK_MODEL = os.getenv("TRANSCRIBE_FALLBACK_MODEL", "gemini-3.1-flash-lite").strip()

# 5. Uzun audio (> 55 daqiqa) yoki transkripsiya bo'sh bo'lganda
LONG_AUDIO_MODEL = os.getenv("LONG_AUDIO_MODEL", "gemini-3.1-flash-lite").strip()
LONG_AUDIO_FALLBACK_MODEL = os.getenv("LONG_AUDIO_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()

# Xotirada saqlanadigan oxirgi xabarlar soni
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

# Vaqtinchalik fayllar va ma'lumotlar papkasi
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "bot_memory.db"

# Tizim yo'riqnomasi (System prompt)
SYSTEM_INSTRUCTION = """Siz do'stona, juda aqlli va har tomonlama yordam beruvchi sun'iy intellekt yordamchisisiz.
Qoidalarga qat'iy rioya qiling:
1. Foydalanuvchi sizga qaysi tilda yozsa yoki gapirsa, faqat o'sha tilda javob qaytaring (O'zbek tilida yozsa - o'zbekcha, Rus tilida yozsa - ruscha, Ingliz tilida yozsa - inglizcha va h.k.).
2. Javoblaringiz tushunarli, aniq, muloyim va foydali bo'lsin.
3. Agar foydalanuvchi audio yoki ovozli xabar yuborsa, audio mazmunini to'liq inobatga oling va berilgan vazifalarni (savolga javob, test tuzish, reja tuzish va boshqalar) bekamu ko'st bajaring.
4. Javoblaringizni Telegram formatiga moslab, chiroyli qilib tartiblang.
5. Muhim: Javoblaringizda keraksiz yulduzchalarni (*) yoki (**) ishlatmang. Ro'yxatlar uchun nuqta (•) yoki chiziqcha (-) belgisidan foydalaning.
"""
