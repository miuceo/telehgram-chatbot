import os
import logging
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from google import genai
from google.genai import types

import config
import database

logger = logging.getLogger(__name__)

FRIENDLY_LIMIT_MSG = "⚠️ Bugungi bepul limit tugadi, keyinroq urinib ko'ring."

def get_audio_duration_seconds(file_path: Path) -> float:
    """ffprobe orqali audio davomiyligini aniqlaydi (soniyalarda)."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        return float(out) if out else 0.0
    except Exception as e:
        logger.warning(f"Audio davomiyligini ffprobe orqali o'qib bo'lmadi: {e}")
        return 0.0

def split_audio_into_chunks(file_path: Path, chunk_duration_sec: int = 1200) -> List[Path]:
    """Audio faylni ~20 daqiqalik (1200 soniya) bo'laklarga ajratadi."""
    out_pattern = config.TEMP_DIR / f"{file_path.stem}_part_%03d{file_path.suffix}"
    cmd = [
        "ffmpeg", "-y", "-i", str(file_path),
        "-f", "segment", "-segment_time", str(chunk_duration_sec),
        "-c", "copy",
        str(out_pattern)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        # Agar stream copy o'xshamasa, re-encode bilan urinib ko'rish
        cmd_reencode = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-f", "segment", "-segment_time", str(chunk_duration_sec),
            "-c:a", "libmp3lame",
            str(out_pattern)
        ]
        subprocess.run(cmd_reencode, capture_output=True, text=True, check=True)

    chunks = sorted(config.TEMP_DIR.glob(f"{file_path.stem}_part_*{file_path.suffix}"))
    return chunks

class AIService:
    def __init__(self):
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if not self._client:
            api_key = config.GEMINI_API_KEY
            if not api_key:
                raise ValueError("GEMINI_API_KEY topilmadi. Iltimos .env fayliga kalitni kiriting.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _call_model(self, model_name: str, contents: list, system_instruction: str = None) -> str:
        """Berilgan modelga so'rov jo'natadi va matnni qaytaradi."""
        # Gemma va Transcribe modellari API darajasida system_instruction parametrini qabul qilmaydi
        supports_sys_instruction = not (
            "gemma" in model_name.lower() or "transcribe" in model_name.lower()
        )
        
        gen_kwargs = {
            "temperature": 0.7,
            "http_options": types.HttpOptions(
                timeout=15000,  # 15 soniya maksimal kutish
                retry_options=types.HttpRetryOptions(attempts=1)
            )
        }
        if supports_sys_instruction and (system_instruction or config.SYSTEM_INSTRUCTION):
            gen_kwargs["system_instruction"] = system_instruction or config.SYSTEM_INSTRUCTION

        gen_config = types.GenerateContentConfig(**gen_kwargs)
        response = self.client.models.generate_content(
            model=model_name,
            contents=contents,
            config=gen_config,
        )
        if response and response.text:
            return response.text.strip()
        elif response and response.candidates:
            parts_text = []
            for c in response.candidates:
                if c.content and c.content.parts:
                    for p in c.content.parts:
                        if hasattr(p, "text") and p.text:
                            parts_text.append(p.text)
                        elif hasattr(p, "audio_transcription") and p.audio_transcription:
                            trans_obj = p.audio_transcription
                            if hasattr(trans_obj, "text") and trans_obj.text:
                                parts_text.append(trans_obj.text)
            if parts_text:
                return "\n".join(parts_text).strip()
        return ""

    def execute_with_fallback(
        self,
        primary_model: str,
        fallback_model: str,
        contents: list,
        system_instruction: str = None,
        task_name: str = ""
    ) -> Tuple[str, str, bool]:
        """
        429 (rate limit), 404 (model not found) yoki bo'sh javob bo'lsa,
        fallback model bilan 1 marta qayta urinadi.
        Ikkalasi ham muvaffaqiyatsiz bo'lsa, xushmuomala o'zbekcha xabar qaytaradi.
        Qaytaradi: (natija_matni, ishlagan_model, muvaffaqiyat_holati)
        """
        # 1. Asosiy model bilan urinish
        logger.info(f"[{task_name}] Asosiy modelga so'rov: {primary_model}")
        try:
            res = self._call_model(primary_model, contents, system_instruction)
            if res and res.strip():
                return res, primary_model, True
            else:
                logger.warning(f"[{task_name}] {primary_model} bo'sh javob qaytardi. Fallback modelga o'tilmoqda: {fallback_model}")
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"[{task_name}] {primary_model} xatolik berdi ({e}). Fallback modelga o'tilmoqda: {fallback_model}")

        # 2. Fallback model bilan 1 marta qayta urinish
        logger.info(f"[{task_name}] Zaxira (fallback) modelga so'rov: {fallback_model}")
        try:
            res = self._call_model(fallback_model, contents, system_instruction)
            if res and res.strip():
                return res, fallback_model, True
            else:
                logger.error(f"[{task_name}] Fallback {fallback_model} ham bo'sh javob qaytardi.")
        except Exception as e:
            logger.error(f"[{task_name}] Fallback {fallback_model} ham xatolik berdi: {e}")

        # 3. Agar har ikkala model ham (masalan Gemma serverlari vaqtincha 500/504 berayotgan bo'lsa)
        # foydalanuvchiga xatolik ko'rsatmasdan eng ishonchli bepul Flash model orqali qutqarish
        safety_model = "gemini-3.5-flash-lite"
        if primary_model != safety_model and fallback_model != safety_model:
            logger.info(f"[{task_name}] Qo'shimcha xavfsizlik modeli bilan urinish: {safety_model}")
            try:
                res = self._call_model(safety_model, contents, system_instruction)
                if res and res.strip():
                    return res, safety_model, True
            except Exception as e:
                logger.error(f"[{task_name}] Qo'shimcha model ham xatolik berdi: {e}")

        # Har ikkalasi muvaffaqiyatsiz bo'lsa
        return FRIENDLY_LIMIT_MSG, fallback_model, False

    # ==================== 1. AGENT BRAIN ====================
    def agent_brain_route(self, prompt: str) -> Tuple[str, str, bool]:
        """Agent brain (function calling, tool routing): gemma-4-26b-a4b-it -> fallback: gemini-3.5-flash-lite"""
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        return self.execute_with_fallback(
            primary_model=config.BRAIN_MODEL,
            fallback_model=config.BRAIN_FALLBACK_MODEL,
            contents=contents,
            task_name="Agent brain"
        )

    # ==================== 2. TEXT (CHAT, SUMMARIZE, TRANSLATE, QUIZ) ====================
    def chat_text(self, user_id: int, user_text: str) -> Tuple[str, bool, str]:
        """
        Text: chat, summarize, translate, quiz: gemma-4-31b-it -> fallback: gemma-4-26b-a4b-it
        Qaytaradi: (javob, muvaffaqiyat, ishlatilgan_model)
        """
        history = database.get_chat_history(user_id, limit=config.MAX_HISTORY_MESSAGES)
        contents = []
        for item in history:
            contents.append(types.Content(
                role=item["role"],
                parts=[types.Part.from_text(text=item["content"])]
            ))

        last_trans = database.get_last_transcription(user_id)
        prompt_to_send = user_text
        if last_trans and len(history) <= 2:
            prompt_to_send += f"\n\n[Kontekst uchun audio matni: {last_trans[:1000]}...]"

        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_to_send)]
        ))

        reply_text, model_used, success = self.execute_with_fallback(
            primary_model=config.WRITER_MODEL,
            fallback_model=config.WRITER_FALLBACK_MODEL,
            contents=contents,
            task_name="Text: chat"
        )

        if success:
            database.save_message(user_id, "user", user_text)
            database.save_message(user_id, "model", reply_text)

        return reply_text, success, model_used

    # ==================== 3. IMAGE UNDERSTANDING ====================
    def chat_image(self, user_id: int, image_bytes: bytes, mime_type: str, caption: str = "") -> Tuple[str, bool, str]:
        """
        Image understanding: gemma-4-31b-it -> fallback: gemini-3.5-flash-lite
        Qaytaradi: (javob, muvaffaqiyat, ishlatilgan_model)
        """
        history = database.get_chat_history(user_id, limit=4)
        contents = []
        for item in history:
            contents.append(types.Content(
                role=item["role"],
                parts=[types.Part.from_text(text=item["content"])]
            ))

        user_prompt = caption.strip() if caption else "Ushbu rasmda nima tasvirlanganini batafsil tushuntirib bering."
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        text_part = types.Part.from_text(text=user_prompt)

        contents.append(types.Content(
            role="user",
            parts=[image_part, text_part]
        ))

        reply_text, model_used, success = self.execute_with_fallback(
            primary_model=config.VISION_MODEL,
            fallback_model=config.VISION_FALLBACK_MODEL,
            contents=contents,
            task_name="Image understanding"
        )

        if success:
            database.save_message(user_id, "user", f"[Rasm yuborildi: {user_prompt}]")
            database.save_message(user_id, "model", reply_text)

        return reply_text, success, model_used

    # ==================== 4. AUDIO TRANSCRIPTION & TASKS ====================
    def _transcribe_file(self, audio_path: Path, mime_type: str, primary_model: str, fallback_model: str) -> Tuple[str, str, bool]:
        """Bitta audio faylni transkripsiya qiladi."""
        uploaded_file = None
        try:
            uploaded_file = self.client.files.upload(
                file=str(audio_path),
                config=types.UploadFileConfig(mime_type=mime_type)
            )
            transcribe_prompt = (
                "Ushbu audiodagi butun nutqni so'zma-so'z, aniq va to'liq matnga (transkripsiyaga) aylantirib bering. "
                "Hech qanday so'zni tashlab ketmang. Faqat eshitilgan so'zlarni yozing."
            )
            contents = [
                types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type or mime_type),
                types.Part.from_text(text=transcribe_prompt)
            ]

            return self.execute_with_fallback(
                primary_model=primary_model,
                fallback_model=fallback_model,
                contents=contents,
                task_name="Audio transcription"
            )
        finally:
            if uploaded_file and hasattr(uploaded_file, "name"):
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass

    def process_audio(
        self,
        user_id: int,
        audio_file_path: Path,
        mime_type: str,
        user_instruction: str = ""
    ) -> Tuple[str, str, bool, str, str]:
        """
        Audio qayta ishlash:
        - Audio <= 55 min: gemini-3.5-transcribe -> fallback: gemini-3.1-flash-lite
        - Audio > 55 min yoki transkripsiya bo'sh/muvaffaqiyatsiz bo'lsa:
          gemini-3.1-flash-lite (20 daqiqalik qismlarga bo'lib) -> fallback: gemini-3.5-flash-lite
        - Ketma-ket vazifa (quiz, xulosa, savol-javob):
          gemma-4-31b-it -> fallback: gemma-4-26b-a4b-it
        Qaytaradi: (transkripsiya, javob, muvaffaqiyat, transkripsiya_modeli, tahlil_modeli)
        """
        duration_sec = get_audio_duration_seconds(audio_file_path)
        logger.info(f"Audio fayl davomiyligi: {duration_sec:.1f} soniya ({duration_sec/60:.1f} daqiqa)")

        transcription_text = ""
        trans_model_used = ""
        trans_success = False

        FIFTY_FIVE_MINUTES = 55 * 60  # 3300 seconds

        if duration_sec <= FIFTY_FIVE_MINUTES and duration_sec > 0:
            # <= 55 daqiqa: gemini-3.5-transcribe -> fallback: gemini-3.1-flash-lite
            transcription_text, trans_model_used, trans_success = self._transcribe_file(
                audio_path=audio_file_path,
                mime_type=mime_type,
                primary_model=config.TRANSCRIBE_MODEL,
                fallback_model=config.TRANSCRIBE_FALLBACK_MODEL
            )

        # Agar davomiylik > 55 min bo'lsa YOKI transkripsiya bo'sh/muvaffaqiyatsiz bo'lsa:
        if duration_sec > FIFTY_FIVE_MINUTES or not trans_success or not transcription_text.strip():
            logger.info("Audio > 55 min yoki transkripsiya bo'sh/xato bo'ldi. LONG_AUDIO_MODEL ga o'tilmoqda.")
            chunks = split_audio_into_chunks(audio_file_path, chunk_duration_sec=1200)
            if not chunks:
                chunks = [audio_file_path]

            chunk_texts = []
            last_model = config.LONG_AUDIO_MODEL
            for chunk in chunks:
                c_text, c_model, c_ok = self._transcribe_file(
                    audio_path=chunk,
                    mime_type=mime_type,
                    primary_model=config.LONG_AUDIO_MODEL,
                    fallback_model=config.LONG_AUDIO_FALLBACK_MODEL
                )
                last_model = c_model
                if c_text and c_text != FRIENDLY_LIMIT_MSG:
                    chunk_texts.append(c_text)
                # Vaqtinchalik bo'lakni o'chirish
                if chunk != audio_file_path and chunk.exists():
                    try:
                        chunk.unlink()
                    except Exception:
                        pass

            trans_model_used = last_model
            transcription_text = "\n\n".join(chunk_texts).strip()
            trans_success = bool(transcription_text)

        if not trans_success:
            return "", FRIENDLY_LIMIT_MSG, False, trans_model_used, ""

        # Transkripsiyani bazada saqlash
        database.save_last_transcription(user_id, transcription_text)

        # 2-bosqich: Matnli vazifa (quiz, xulosa, savolga javob)
        # WRITER_MODEL: gemma-4-31b-it -> fallback: gemma-4-26b-a4b-it
        if user_instruction and user_instruction.strip():
            task_prompt = (
                f"Foydalanuvchi audioni yuborib quyidagi vazifani berdi:\n"
                f"\"{user_instruction.strip()}\"\n\n"
                f"Quyidagi audio matni asosida ushbu vazifani to'liq bajaring:\n"
                f"--- AUDIO MATNI ---\n{transcription_text}\n--- TUGADI ---"
            )
        else:
            task_prompt = (
                "Quyidagi matn foydalanuvchining ovozli xabari yoki audiosi transkripsiyasidir:\n"
                f"\"{transcription_text}\"\n\n"
                "Ko'rsatma:\n"
                "- Agar foydalanuvchi savol so'ragan yoki biror ma'lumot so'ragan bo'lsa, unga to'g'ridan-to'g'ri, samimiy va to'liq javob qaytaring (hech qanday 'Tahlil:', 'Foydalanuvchi so'radi:' kabi ortiqcha kirish so'zlarsiz, xuddi suhbatdoshdek javob bering).\n"
                "- Agar bu ma'ruza yoki darslik bo'lsa, uning qisqacha mazmuni va asosiy xulosalarini keltiring."
            )

        task_contents = [types.Content(role="user", parts=[types.Part.from_text(text=task_prompt)])]
        reply_text, writer_model_used, writer_success = self.execute_with_fallback(
            primary_model=config.WRITER_MODEL,
            fallback_model=config.WRITER_FALLBACK_MODEL,
            contents=task_contents,
            task_name="Audio post-task"
        )

        # Suhbat tarixiga yozish
        preview = transcription_text[:200].replace('\n', ' ')
        database.save_message(user_id, "user", f"[Audio yuborildi. Matn: {preview}...]")
        database.save_message(user_id, "model", reply_text)

        return transcription_text, reply_text, writer_success, trans_model_used, writer_model_used

    # ==================== 5. DOCUMENT & CODE ANALYSIS ====================
    def process_document(
        self,
        user_id: int,
        file_path: Path,
        mime_type: str,
        user_instruction: str = ""
    ) -> Tuple[str, bool, str]:
        """Hujjat yoki kod faylini (html, txt, pdf, py, json va h.k.) tahlil qiladi."""
        prompt = user_instruction.strip() if user_instruction else "Ushbu fayl mazmunini tahlil qiling va asosiy fikrlarini tushuntirib bering."
        uploaded_file = None
        try:
            text_extensions = [".html", ".htm", ".txt", ".py", ".json", ".js", ".css", ".md", ".csv", ".xml", ".sql", ".sh", ".env"]
            if file_path.suffix.lower() in text_extensions:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 150000:
                    content = content[:150000] + "\n...[Fayl juda uzun bo'lganligi sababli qisqartirildi]..."

                task_prompt = (
                    f"Foydalanuvchi quyidagi faylni ({file_path.name}) yubordi va vazifa berdi:\n"
                    f"\"{prompt}\"\n\n"
                    f"--- FAYL MATNI ({file_path.name}) ---\n{content}\n--- FAYL TUGADI ---\n\n"
                    "Fayl kodi yoki matni asosida foydalanuvchining savoliga to'liq, professional va foydali javob bering."
                )
                contents = [types.Content(role="user", parts=[types.Part.from_text(text=task_prompt)])]
            else:
                # PDF yoki boshqa binar hujjatlar uchun Files API
                uploaded_file = self.client.files.upload(
                    file=str(file_path),
                    config=types.UploadFileConfig(mime_type=mime_type or "application/octet-stream")
                )
                contents = [
                    types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type or mime_type),
                    types.Part.from_text(text=f"Ushbu fayl ({file_path.name}) bo'yicha vazifa: {prompt}")
                ]

            reply_text, model_used, success = self.execute_with_fallback(
                primary_model=config.WRITER_MODEL,
                fallback_model=config.WRITER_FALLBACK_MODEL,
                contents=contents,
                task_name="Document analysis"
            )

            if success:
                database.save_message(user_id, "user", f"[Fayl yuborildi: {file_path.name}. Buyruq: {prompt}]")
                database.save_message(user_id, "model", reply_text)

            return reply_text, success, model_used
        except Exception as e:
            logger.error(f"process_document xatosi: {e}")
            return f"⚠️ Faylni tahlil qilishda xatolik yuz berdi: {e}", False, ""
        finally:
            if uploaded_file and hasattr(uploaded_file, "name"):
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass

ai_service = AIService()
