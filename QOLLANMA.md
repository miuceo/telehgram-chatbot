# 🤖 Telegram Aqlli AI Boti — Foydalanish Qo'llanmasi

Ushbu bot **Google Gemini** sun'iy intellekti bilan ishlaydi va **100% bepul**. Dasturlashni bilishingiz shart emas — quyidagi 2 ta oddiy qadamni bajarsangiz kifoya.

---

## 🚀 1-QADAM: Maxfiy kalitlaringizni kiritish

Papka ichida `.env` degan fayl bor. Uni o'zingizga qulay matn tahrirlovchi (masalan: **Bloknot / Notepad**) bilan oching.

Unda quyidagi 2 ta qatorni o'z kalitlaringiz bilan almashtiring:

```env
TELEGRAM_BOT_TOKEN=bu_yerga_botfather_bergan_tokonni_yozing
GEMINI_API_KEY=bu_yerga_google_ai_studio_kalitini_yozing
```

* 🔹 **Telegram Bot Token**: Telegram'dagi `@BotFather` botiga kirib, `/newbot` buyrug'i orqali yangi bot yaratib olgan kalitingiz.
* 🔹 **Google AI Studio Kaliti**: [aistudio.google.com](https://aistudio.google.com/) saytiga Google hisobingiz bilan kirib, **"Get API key"** tugmasini bosib bepul olgan kalitingiz.

Faylni saqlang (**Ctrl + S**) va yoping.

---

## ⚡️ 2-QADAM: Botni ishga tushirish

Papkadagi **`ishga_tushirish.bat`** fayli ustiga sichqoncha bilan **ikki marta bosing**.

Qora oyna ochiladi va:
```text
🤖 Telegram Bot ishga tushirilmoqda...
Xabarlarni kutish boshlandi (Polling)...
```
degan yozuv chiqadi. **Bo'ldi! Botingiz ishga tushdi va xabarlarni kutmoqda!**

*(Eslatma: Bot ishlashi uchun ushbu qora oyna ochiq turishi kerak. Botni o'chirish uchun oynani yopishingiz kifoya).*

---

## 🎯 Bot nimalar qila oladi?

1. **Aqlli suhbat va Xotira:**
   * Istalgan tilda (O'zbek, Rus, Ingliz va h.k.) yozing — aqlli suhbatdosh kabi o'sha tilda javob beradi.
   * Suhbatdagi oldingi gaplaringizni eslab qoladi.

2. **Rasm tahlili:**
   * Botga istalgan rasmni yuboring va savol bering (masalan: *"Bu yerda nima yozilgan?"*, *"Bu nima?"*). Rasm mazmunini darhol tahlil qiladi.

3. **Ovozli xabar va Katta audiolarni matnga aylantirish:**
   * Mikrofonni bosib ovozli xabar yuboring yoki fayl sifatida audio (ma'ruza) tashlang.
   * Bot audioni to'liq eshitib, uning matnini **`.txt` fayl** qilib taqdim etadi.
   * Agar audioda savol bo'lsa — to'g'ridan-to'g'ri javob beradi.

4. **Ketma-ket murakkab vazifalar:**
   * Masalan, audioni yuborib izohiga: *«Shundan 10 ta test tuzib ber»* yoki *«Qisqacha konspekt qilib ber»* deb yozing.
   * Bot avval audioning matnini `.txt` fayl qilib beradi, so'ngra test yoki konspektni xabarda yozib beradi.

5. **Uzun matnlar:**
   * Agar javob yoki darslik matni Telegram sig'imidan uzun bo'lsa, bot uni avtomatik `.txt` fayl qilib yuboradi.

6. **Tugmalar:**
   * **«🗑 Suhbatni tozalash»** — Bot xotirasini yangilab, yangi mavzuni noldan boshlash.
   * **«📊 Xotira holati»** — Bot xotirasida nechta xabar saqlanayotganini ko'rish.
   * **«ℹ️ Yordam»** — Bot haqida qisqacha yo'riqnoma.

---

## 🔒 Xavfsizlik va Bepul limitlar

* Sizning kalitlaringiz faqat o'z kompyuteringizdagi `.env` faylida saqlanadi va begonalarga ko'rinmaydi.
* Google AI Studio bepul versiyasida har kuni minglab so'rovlar bepul beriladi. Agar bepul limit tugasa, bot qotib qolmaydi, balki: *«Bugungi bepul so'rovlar limiti tugadi, iltimos ertaga urinib ko'ring»* deb xabar beradi.
