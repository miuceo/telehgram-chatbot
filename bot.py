import io
import os
import re
import html
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
import database
from ai_service import ai_service

class RenderHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram AI Bot is running 24/7 on Render!")

    def log_message(self, format, *args):
        pass  # Server jurnali toza turishi uchun

def start_health_server():
    """Render yoki boshqa bulutli serverlar uchun $PORT da ishlovchi health check server."""
    port_str = os.getenv("PORT", "").strip()
    if port_str:
        try:
            port = int(port_str)
            server = HTTPServer(("0.0.0.0", port), RenderHealthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            logger.info(f"Render Health Server {port}-portda ishga tushirildi.")
        except Exception as e:
            logger.warning(f"Health serverni ishga tushirishda xatolik: {e}")

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Asosiy doimiy klaviatura
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🗑 Suhbatni tozalash", "ℹ️ Yordam"],
        ["📊 Xotira holati"]
    ],
    resize_keyboard=True
)

def format_for_telegram(text: str) -> str:
    """Markdown belgilarini (**, *, #) toza va chiroyli Telegram HTML formatiga aylantiradi, yulduzchalarni yo'qotadi."""
    if not text:
        return ""
    
    # 0. Allaqachon mavjud xavfsiz HTML teglarni saqlash
    safe_tags = ['b', 'i', 'code', 'pre', 'blockquote']
    for tag in safe_tags:
        text = text.replace(f'<{tag}>', f'___TAG_{tag}_OPEN___')
        text = text.replace(f'</{tag}>', f'___TAG_{tag}_CLOSE___')

    # 1. Kod bloklarini vaqtinchalik saqlash
    code_blocks = []
    def save_code_block(m):
        code_blocks.append(f"<pre>{html.escape(m.group(1), quote=False)}</pre>")
        return f"___CODE_BLOCK_{len(code_blocks)-1}___"
    
    text = re.sub(r'```(?:[a-zA-Z0-9_+-]+)?\n?(.*?)```', save_code_block, text, flags=re.DOTALL)
    
    # 2. Qator ichidagi kodlarni saqlash
    inline_codes = []
    def save_inline_code(m):
        inline_codes.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        return f"___INLINE_CODE_{len(inline_codes)-1}___"
    
    text = re.sub(r'`([^`]+)`', save_inline_code, text)
    
    # 3. HTML maxsus belgilarini xavfsiz qilish (<, >, &)
    text = html.escape(text, quote=False)

    # Saqlangan teglarni qaytarish
    for tag in safe_tags:
        text = text.replace(f'___TAG_{tag}_OPEN___', f'<{tag}>')
        text = text.replace(f'___TAG_{tag}_CLOSE___', f'</{tag}>')
    
    # 4. Sarlavhalar (# Sarlavha -> <b>Sarlavha</b>)
    text = re.sub(r'(?m)^#{1,6}\s*(.+?)$', r'<b>\1</b>', text)
    
    # 5. Ro'yxatlar (* element yoki - element -> • element)
    text = re.sub(r'(?m)^[\*\-]\s+', '• ', text)
    
    # 6. Qalin matn (**matn** -> <b>matn</b>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # 7. Kursiv (*matn* yoki _matn_ -> <i>matn</i>)
    text = re.sub(r'(?<!\w)\*([^\*\n]+?)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_([^_\n]+?)_(?!\w)', r'<i>\1</i>', text)
    
    # 8. Iqtiboslar (> matn -> ▎ matn)
    text = re.sub(r'(?m)^&gt;\s?', '▎ ', text)
    
    # 9. Qolgan ortiqcha yulduzchalarni to'liq tozalash
    text = text.replace('**', '').replace('*', '')
    
    # 10. Kod bloklarini qaytarish
    for i, cb in enumerate(code_blocks):
        text = text.replace(f"___CODE_BLOCK_{i}___", cb)
    for i, ic in enumerate(inline_codes):
        text = text.replace(f"___INLINE_CODE_{i}___", ic)
        
    return text.strip()

async def safe_reply(update: Update, text: str, reply_markup=None):
    """Xabarni xavfsiz jo'natadi (HTML orqali, xatolik yuz bersa yulduzchalarsiz toza matn ko'rinishida yuboradi)."""
    formatted = format_for_telegram(text)
    try:
        return await update.message.reply_text(
            formatted,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except Exception:
        clean_text = re.sub(r'<[^>]+>', '', formatted)
        clean_text = clean_text.replace('**', '').replace('*', '')
        return await update.message.reply_text(
            clean_text,
            parse_mode=None,
            reply_markup=reply_markup
        )

async def send_text_or_file(update: Update, text: str, filename_prefix: str = "javob", caption_prefix: str = ""):
    """Agar matn uzun bo'lsa (3800 belgidan ko'p), uni .txt fayl qilib yuboradi."""
    if len(text) <= 3800:
        await safe_reply(update, text)
    else:
        # Fayl sifatida yuborish
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.txt"
        file_bytes = io.BytesIO(text.encode("utf-8"))
        file_bytes.name = filename
        
        caption = caption_prefix or "📄 Matn uzun bo'lganligi sababli to'liq holatda .txt fayl qilib yuborildi."
        if len(caption) > 1000:
            caption = caption[:1000] + "..."
            
        await update.message.reply_document(
            document=file_bytes,
            filename=filename,
            caption=caption
        )

# ==================== BUYRUQLAR (COMMANDS) ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi /start bosganda xush kelibsiz xabari."""
    user = update.effective_user
    first_name = user.first_name if user else "Do'stim"
    
    welcome_text = (
        f"Assalomu alaykum, {first_name}! 👋\n\n"
        "Men sizning ko'p funksiyali aqlli AI yordamchingizman. Quyidagi ishlarni bajara olaman:\n\n"
        "💬 **Oddiy suhbat:** Menga istalgan tilda xabar yozing, aqlli suhbatdoshdek javob beraman.\n"
        "🖼 **Rasmlar tahlili:** Rasm yuboring va savolingizni bering — rasmda nima borligini aytib beraman.\n"
        "🎙 **Ovozli xabarlar va Audiolar:** Ovoz yoki audio yozuv (ma'ruza) yuborsangiz, uni to'liq matnga (.txt fayl) aylantirib beraman va savollaringizga javob qaytaraman.\n"
        "📝 **Murakkab vazifalar:** Masalan, audio yuborib *«Shundan test tuzib ber»* yoki *«Qisqacha xulosa chiqar»* desangiz, hammasini ketma-ket bajaraman.\n"
        "🧠 **Xotira:** Oldingi gaplashgan mavzularimizni eslab turaman.\n\n"
        "Quyidagi tugmalar orqali suhbatni boshqarishingiz mumkin:"
    )
    await safe_reply(update, welcome_text, reply_markup=MAIN_KEYBOARD)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam va yo'riqnoma xabari."""
    help_text = (
        "ℹ️ **Botdan foydalanish bo'yicha qo'llanma:**\n\n"
        "1. **Matn yozish:**\n"
        "Shunchaki savolingiz yoki xabaringizni yuboring. O'zbek, rus, ingliz yoki boshqa tillarda yozishingiz mumkin.\n\n"
        "2. **Ovozli xabar va audio yuborish:**\n"
        "• Mikrofonni bosib ovoz yozib yuboring.\n"
        "• Yoki telefon/kompyuteringizdagi audio faylni (mp3, m4a, ogg, wav) jo'nating.\n"
        "• Bot audioni eshitib, uning to'liq matnini **.txt fayl** sifatida taqdim etadi.\n"
        "• Agar audioda savol so'ralgan bo'lsa, unga to'liq javob beradi.\n"
        "• Audio bilan birga matn ham yozishingiz mumkin (masalan, *«Shundan 5 ta test tuz»*).\n\n"
        "3. **Rasm yuborish:**\n"
        "Istalgan rasmni yuboring (izohiga savol yozsangiz ham bo'ladi). Bot rasm mazmunini tushunadi.\n\n"
        "4. **Suhbatni tozalash:**\n"
        "Yangi mavzuni noldan boshlash uchun **«🗑 Suhbatni tozalash»** tugmasini bosing."
    )
    await safe_reply(update, help_text, reply_markup=MAIN_KEYBOARD)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suhbat tarixini tozalash."""
    user_id = update.effective_user.id
    database.clear_chat_history(user_id)
    await safe_reply(
        update,
        "✅ **Suhbat tarixi tozalandi!**\n\nEndi noldan yangi mavzuda gaplashishimiz mumkin.",
        reply_markup=MAIN_KEYBOARD
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xotira va bot holatini ko'rish."""
    user_id = update.effective_user.id
    history = database.get_chat_history(user_id)
    last_trans = database.get_last_transcription(user_id)
    
    trans_status = "Mavjud (oxirgi audio eslab qolingan)" if last_trans else "Hozircha yo'q"
    
    status_text = (
        "📊 <b>Bot va Xotira holati:</b>\n\n"
        f"• Suhbat xotirasidagi xabarlar: <b>{len(history)} ta</b> (Maksimal: {config.MAX_HISTORY_MESSAGES})\n"
        f"• Oxirgi audio xotirasi: <b>{trans_status}</b>\n\n"
        "🤖 <b>Sozlangan AI Modellari:</b>\n"
        f"• Matn & Suhbat: <code>{config.WRITER_MODEL}</code>\n"
        f"• Rasmlar tahlili: <code>{config.VISION_MODEL}</code>\n"
        f"• Audio (<=55 daq): <code>{config.TRANSCRIBE_MODEL}</code>\n"
        f"• Uzun audio (>55 daq): <code>{config.LONG_AUDIO_MODEL}</code>\n"
        f"• Agent miyasi: <code>{config.BRAIN_MODEL}</code>\n\n"
        "Xizmat turi: <b>100% Bepul kvota</b>\n"
        "Xotirani tozalash uchun: <b>«🗑 Suhbatni tozalash»</b>"
    )
    await safe_reply(update, status_text, reply_markup=MAIN_KEYBOARD)

async def typing_loop(bot, chat_id: int, stop_event: asyncio.Event):
    """Javob tayyor bo'lguncha Telegram'da 'yozmoqda...' holatini yangilab turadi."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass

# ==================== MATNLI XABARLAR ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining oddiy matn xabarlarini qayta ishlash."""
    user_text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Klaviatura tugmalarini tekshirish
    if user_text == "🗑 Suhbatni tozalash":
        return await reset_command(update, context)
    elif user_text == "ℹ️ Yordam":
        return await help_command(update, context)
    elif user_text == "📊 Xotira holati":
        return await status_command(update, context)

    # Foydalanuvchiga bot ishlayotganini ko'rsatish
    status_msg = await update.message.reply_text("🧠 Javob tayyorlanmoqda...")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context.bot, chat_id, stop_typing))

    try:
        reply_text, success, model_used = await asyncio.to_thread(ai_service.chat_text, user_id, user_text)
        stop_typing.set()
        await typing_task
        await status_msg.delete()
        await send_text_or_file(update, reply_text, filename_prefix="javob")
    except Exception as e:
        stop_typing.set()
        await typing_task
        logger.error(f"handle_text xatosi: {e}")
        await status_msg.edit_text("⚠️ Kechirasiz, javob tayyorlashda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")

# ==================== RASMLARNI QAYTA ISHLASH ====================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi rasm yuborganda qayta ishlash."""
    user_id = update.effective_user.id
    caption = update.message.caption or ""

    status_msg = await update.message.reply_text("⏳ Rasm yuklab olinmoqda va tahlil qilinmoqda...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        await status_msg.edit_text("🧠 Rasm tahlil qilinmoqda...")
        reply_text, success, model_used = await asyncio.to_thread(
            ai_service.chat_image, user_id, bytes(image_bytes), "image/jpeg", caption
        )
        
        await status_msg.delete()
        await send_text_or_file(update, reply_text, filename_prefix="rasm_tahlili")
    except Exception as e:
        logger.error(f"handle_photo xatosi: {e}")
        await status_msg.edit_text("⚠️ Rasmni qayta ishlashda xatolik yuz berdi. Iltimos qaytadan yuborib ko'ring.")

# ==================== OVOZ VA AUDIO FAYLLARNI QAYTA ISHLASH ====================

async def handle_voice_or_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ovozli xabar yoki audio fayllarni qayta ishlash."""
    user_id = update.effective_user.id
    caption = update.message.caption or ""
    
    voice = update.message.voice
    audio = update.message.audio
    document = update.message.document

    # Fayl identifikatorini va ma'lumotlarini aniqlash
    file_id = None
    file_size = 0
    file_ext = ".ogg"
    mime_type = "audio/ogg"

    if voice:
        file_id = voice.file_id
        file_size = voice.file_size or 0
        file_ext = ".ogg"
        mime_type = "audio/ogg"
    elif audio:
        file_id = audio.file_id
        file_size = audio.file_size or 0
        file_ext = Path(audio.file_name or "audio.mp3").suffix or ".mp3"
        mime_type = audio.mime_type or "audio/mpeg"
    elif document:
        # Hujjat ko'rinishida yuborilgan audio fayllar
        doc_name = (document.file_name or "").lower()
        if any(doc_name.endswith(ext) for ext in [".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".opus", ".wma"]):
            file_id = document.file_id
            file_size = document.file_size or 0
            file_ext = Path(doc_name).suffix
            mime_type = document.mime_type or "audio/mpeg"
        else:
            return  # Audio bo'lmagan hujjatlarni e'tiborsiz qoldirish

    if not file_id:
        return

    # Telegram bot 20 MB dan katta fayllarni yuklay olmaydi
    MAX_SIZE = 20 * 1024 * 1024  # 20 MB
    if file_size > MAX_SIZE:
        size_mb = file_size / (1024 * 1024)
        await safe_reply(
            update,
            f"⚠️ **Fayl hajmi juda katta ({size_mb:.1f} MB)**\n\n"
            "Telegram rasmiy bot tizimi bitta faylni yuklab olishda ko‘pi bilan **20 MB** qabul qila oladi.\n"
            "Iltimos, audioni qisqartirib yoki bo'lib yuboring."
        )
        return

    status_msg = await update.message.reply_text("⏳ Audio fayl yuklab olinmoqda...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE)

    temp_audio_path = None
    try:
        tg_file = await context.bot.get_file(file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_audio_path = config.TEMP_DIR / f"audio_{user_id}_{timestamp}{file_ext}"
        
        await tg_file.download_to_drive(custom_path=temp_audio_path)

        await status_msg.edit_text("✍️ Nutq to'liq matnga aylantirilmoqda (transkripsiya)...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # AI orqali transkripsiya va tahlil
        transcription, reply_text, success, trans_model, writer_model = await asyncio.to_thread(
            ai_service.process_audio,
            user_id,
            temp_audio_path,
            mime_type,
            caption
        )

        if not success:
            await status_msg.edit_text(reply_text)
            return

        await status_msg.edit_text("📤 Natijalar yuborilmoqda...")

        # 1. Transkripsiya matnini .txt fayl qilib yuborish
        trans_filename = f"transkripsiya_{timestamp}.txt"
        trans_bytes = io.BytesIO(transcription.encode("utf-8"))
        trans_bytes.name = trans_filename

        await update.message.reply_document(
            document=trans_bytes,
            filename=trans_filename,
            caption="🎙 **Audioning to'liq matni (transkripsiya)**"
        )

        # 2. Savolga javob, test yoki tahlil matnini yuborish
        await send_text_or_file(
            update,
            reply_text,
            filename_prefix="tahlil_natijasi",
            caption_prefix="📋 Tahlil natijasi uzun bo'lganligi sababli fayl shaklida yuborildi."
        )

        # Jarayon xabarini tozalash
        await status_msg.delete()

    except Exception as e:
        logger.error(f"handle_voice_or_audio xatosi: {e}")
        await status_msg.edit_text("⚠️ Audioni qayta ishlashda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
    finally:
        # Vaqtinchalik faylni o'chirish
        if temp_audio_path and temp_audio_path.exists():
            try:
                temp_audio_path.unlink()
            except Exception:
                pass

# ==================== HUJJATLAR VA KOD FAYLLARINI QAYTA ISHLASH ====================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hujjatlar (HTML, TXT, PDF, Python, JSON va h.k.) ni qayta ishlash."""
    document = update.message.document
    if not document:
        return

    doc_name = (document.file_name or "").lower()
    audio_extensions = [".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".opus", ".wma"]
    if any(doc_name.endswith(ext) for ext in audio_extensions):
        return await handle_voice_or_audio(update, context)

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""

    status_msg = await update.message.reply_text(f"⏳ Fayl yuklab olinmoqda va tahlil qilinmoqda ({document.file_name})...")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context.bot, chat_id, stop_typing))

    temp_path = None
    try:
        tg_file = await context.bot.get_file(document.file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = config.TEMP_DIR / f"doc_{user_id}_{timestamp}_{document.file_name}"
        await tg_file.download_to_drive(custom_path=temp_path)

        reply_text, success, model_used = await asyncio.to_thread(
            ai_service.process_document,
            user_id,
            temp_path,
            document.mime_type or "",
            caption
        )

        stop_typing.set()
        await typing_task
        await status_msg.delete()
        await send_text_or_file(update, reply_text, filename_prefix="fayl_tahlili")
    except Exception as e:
        stop_typing.set()
        await typing_task
        logger.error(f"handle_document xatosi: {e}")
        await status_msg.edit_text("⚠️ Faylni qayta ishlashda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

# ==================== XATOLIKLARNI USHLASH ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global xatoliklar ushlanganda bot to'xtab qolmasligini ta'minlaydi."""
    logger.error("Xatolik yuz berdi: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ **Kutilmagan xatolik yuz berdi.**\n"
                "Iltimos, bir necha daqiqadan so'ng qayta urinib ko'ring."
            )
        except Exception:
            pass

# ==================== ASOSIY ISHGA TUSHIRISH FUNKSIYASI ====================

def main():
    """Botni ishga tushiruvchi asosiy funksiya."""
    token = config.TELEGRAM_BOT_TOKEN
    gemini_key = config.GEMINI_API_KEY

    if not token or token == "SIZNING_TELEGRAM_BOT_TOKENINGIZ":
        print("\n" + "="*60)
        print("DIQQAT: TELEGRAM_BOT_TOKEN sozlanmagan!")
        print("Iltimos, '.env' faylini oching va bot kalitingizni kiriting.")
        print("="*60 + "\n")
        return

    if not gemini_key or gemini_key == "SIZNING_GEMINI_API_KALITINGIZ":
        print("\n" + "="*60)
        print("DIQQAT: GEMINI_API_KEY sozlanmagan!")
        print("Iltimos, '.env' faylini oching va Google AI kalitingizni kiriting.")
        print("="*60 + "\n")
        return

    # Render uchun $PORT serverini ishga tushirish (agar mavjud bo'lsa)
    start_health_server()

    print("🤖 Telegram Bot ishga tushirilmoqda...")
    print(f"Modul: Writer ({config.WRITER_MODEL}), Vision ({config.VISION_MODEL})")
    print("Xabarlarni kutish boshlandi (Polling)...\n")

    app = ApplicationBuilder().token(token).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tozalash", reset_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("status", status_command))

    # Matnli xabarlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Rasmlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Ovozli xabarlar va audio fayllar
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_or_audio))
    app.add_handler(MessageHandler(filters.AUDIO, handle_voice_or_audio))
    
    # Hujjatlar (HTML, PDF, kod fayllari, matnlar va h.k.)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Xatoliklarni boshqaruvchi
    app.add_error_handler(error_handler)

    # Botni yurgizish
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
