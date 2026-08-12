# Pitch — Phoenix AI

**Kichik tadbirkorlar uchun AI moliyaviy maslahatchi**
*G'oyadan — o'sishgacha*

**Holat:** 2026-yil 12-avgust · Demo hududlar: Toshkent va Navoiy
**Demo:** `npm run dev` → `/` (landing) · `/maslahatchi` (AI chat) · `/biznes-reja` · `/kredit` · `/soliq`
**Tillar:** o'zbek · rus · ingliz (yuqoridagi almashtirgich butun saytni o'zgartiradi)

Har bir slaydda **bitta fikr** va **bitta raqam** bo'lsin. Raqamlar quyida — hammasi
ochiq manbadan, hech biri o'ylab topilmagan.

---

## 1. Muammo (antibiotik, vitamin emas)

> ### Kichik tadbirkor buxgalter yollay olmaydi. Shuning uchun moliyaviy qarorlarni ko'r-ko'rona qabul qiladi — va bu unga **haqiqiy pulga** tushadi.

Uchta qon oqishi:

| Og'riq | Nega hech kim tuzatmaydi |
|---|---|
| 🧾 Noto'g'ri soliq rejimi | Zarar **ko'rinmaydi** — har oy jimgina chiqib ketadi |
| 💰 Ko'tara olmaydigan kredit | Bank oylik to'lovni aytadi, "ko'tara olasizmi" ni **aytmaydi** |
| 🎁 Bilmagan imtiyoz | Bank o'z mahsulotini sotadi, davlat dasturini **reklama qilmaydi** |

**Jury savoliga tayyor javob:** *"Bu bo'lmasa odam nima qiladi?"* → **Hech narsa.
Bilmaganicha qoladi va to'lab yuraveradi.**

---

## 2. Raqam bilan zarba (bitta slayd, bitta raqam)

> # 51 738 912 so'm

200 mln so'mlik kredit, 36 oyga:
· **14%** da (Sanoatqurilishbank) → oyiga 6 835 526
· **28%** da (Hamkorbank) → oyiga 8 272 718

**Ikki barobar farq. Bir xil tadbirkor, bir xil kredit.**
Va u bu farqni ko'rmaydi — chunki bitta bankka boradi.

> *Manba: bank.uz, 12.08.2026 — 30 bankdan 173 taklif. Raqam demo sahifada real vaqtda hisoblanadi.*

---

## 3. Yechim

**Bitta biznes profili → to'rtta asbob → bitta aniq javob.**

| Asbob | Nima aytadi |
|---|---|
| 📊 Biznes-reja | Zararsizlik nuqtasi · kuniga kerakli mijoz · qoplanish muddati → **✅ / ⚠️ / ❌ hukm** |
| 💰 Kredit | Oylik to'lov · ortiqcha to'lov · **kredit yuki** (aylanmaning necha % i) |
| 🎁 Imtiyoz | Yosh, soha, kredit tarixi bo'yicha **loyiqlik tekshiruvi** |
| 🧾 Soliq | 2026 rejimlarini solishtirish → **eng arzoni** |
| 📍 Lokatsiya | Toshkent ↔ Navoiy: bir xil biznes, **boshqa hukm** |

🔑 **Muhim texnik qaror:** hisob-kitobni **AI emas, matematik kod** bajaradi.
AI faqat tushuntiradi. Chunki noto'g'ri raqam = tadbirkorga jarima.

---

## 4. Demo stsenariysi (3 daqiqa, aynan shu tartibda)

**A. Soliq — `/soliq`** (og'riqdan boshlanadi)
Oylik aylanma 70 mln, oziq-ovqat, 2 xodim → **Hisoblash**
> ### "Noto'g'ri rejim sizga 25 200 000 so'm turadi. Har yili."

**B. Imtiyoz — `/kredit`** (eng kuchli lahza)
200 mln, 36 oy, 28%, yosh **26** → **Tekshirish**
> ### "SIZ BILMAGAN IMTIYOZ: 37 520 604 so'm"
> Yoshlar tadbirkorligi — 18%, 7 yil, 1 yil imtiyozli davr
> Ostida: ⚠️ oylik to'lov aylanmangizning 23.6% ini oladi — chegara zona

**C. Lokatsiya — `/biznes-reja`** (yakuniy zarba)
Baraka Market, oziq-ovqat, Toshkent, 150 mln kapital, 2 xodim, 8 mln ijara
> **Toshkent: ❌ tavsiya etilmaydi** · zararsizlik 116.8 mln, kuniga 100 mijoz
> **Navoiy: ⚠️ chegarada** · zararsizlik 99.7 mln, kuniga 86 mijoz, 53 oyda qoplanadi
>
> *"Bir xil biznes, boshqa shahar — natija boshqacha."*

---

## 5. Nega bizga ishonish mumkin (differensiatsiya)

| Kim | Nima deydi |
|---|---|
| Bank | "Sizga kredit bera olamiz." |
| Davlat raqamli kreditlash platformasi (01.07.2026) | "Arizangizni bir nechta bankka yuboramiz." |
| **Phoenix AI** | **"Bu kreditni olmang — aylanmangizning 31% ini yeydi."** |

> **Manfaatlar to'qnashuvi yo'q.** Bank platformasi hech qachon "kredit olmang"
> demaydi — uning ishi kredit berish. Bizning daromadimiz kreditga bog'liq emas.

**Raqobatga munosabat:** qarshi turmaymiz — **eshik bo'lamiz.**
*"Biz tadbirkorni tayyorlaymiz, davlat platformasi rasmiylashtiradi."*

---

## 6. Bozor

- Maqsadli segment: boshlang'ich tadbirkorlar · YaTT/MChJ egalari · biznes talabalari
- **Pul kimdan keladi:** amaldagi YaTT/MChJ egalari
- Talabalar — hajm va kelajakdagi foydalanuvchi (bugungi talaba = ertangi tadbirkor)

> ⚠️ **TO'LDIRISH KERAK:** O'zbekistonda yiliga ro'yxatdan o'tuvchi yangi YaTT/MChJ
> soni — Statistika qo'mitasidan rasmiy raqam. Jury albatta manba so'raydi.

---

## 7. Biznes modeli

1. **Obuna** — tadbirkor to'laydi (asosiy)
2. **Bankdan yo'naltirish** — sifatli qarz oluvchi uchun (keyingi bosqich)
3. **Kengaytma** — buxgalteriya, sug'urta, hisobot xizmatlari

> Deck'da bank logotiplarini "hamkorlarimiz" deb qo'ymang — sherikligingiz yo'q.
> To'g'ri til: *"Hozir ochiq ma'lumot. Sheriklik — keyingi bosqich."*

---

## 8. Texnik asos (jury "bu ishlaydimi?" desa)

| | |
|---|---|
| Baza | 42 000 qator ishlab chiqarishga tayyor kod (FastAPI + Next.js 15) |
| Tayyor | Auth + 2FA · Stripe billing · PDF bilim bazasi · Telegram · 3 til · superadmin panel |
| Qo'shildi | 4 ta moliyaviy hisob kutubxonasi · 4 API endpoint · 4 ta ochiq sahifa · AI maslahatchi (suhbat) · to'liq uz/ru/en |
| Sifat | **43 ta yangi unit test** · ruff toza · eslint toza · TypeScript xatosiz |
| Ma'lumot | 12 bank · 6 imtiyozli dastur · 2026 soliq rejimlari · 4 shahar · 10 soha |

---

## 9. Halollik (bu slayd ishonch qozonadi)

Biz **bilmagan narsalarni bilamiz va yashirmaymiz:**

- Har bir hisobda **taxminlar ochiq ko'rsatilgan** va tahrirlanadi
- Tasdiqlanmagan imtiyozda **"tasdiqlanishi kerak"** belgisi turadi
- Har bir raqamda **manba va sana** bor
- Ijara/ish haqi kabi mahalliy narxlarni **o'ylab topmaymiz** — foydalanuvchidan so'raymiz
- Har sahifada: *"Bu litsenziyalangan moliyaviy maslahat emas"*

---

## 10. Keyingi qadamlar

| Muddat | Ish |
|---|---|
| Darhol | Soliq stavkalarini buxgalter bilan tasdiqlash |
| 1–2 hafta | Tuman toifalari rasmiy ro'yxati · dastur muddatlarini tekshirish |
| 1 oy | AI maslahatchiga til modelini ulash (hozir qoidalar asosida, hisob aniq) |
| 2–3 oy | Bank API integratsiyasi · onlayn ariza · Telegram bot |

---

## Manbalar (deck oxirida bo'lsin)

- [bank.uz — biznes kreditlari](https://bank.uz/uz/corp-credits)
- [Zamin.uz — Yoshlar tadbirkorligi (PQ-210, 01.06.2026)](https://zamin.uz/en/uzbekistan/205335-preferential-loans-for-youth-business-and-education-launch.html)
- [Gazeta.uz — parrandachilik imtiyozli kreditlari](https://www.gazeta.uz/oz/2026/07/24/parrandachilik/)
- [Trend.az — raqamli kreditlash platformasi va imtiyozlar](https://www.trend.az/business/4195344.html)
- [Kun.uz — YaTT uchun 1% aylanma solig'i](https://kun.uz/38873218)
- [Gazeta.uz — QQS chegarasi 5 mlrd so'mga](https://www.gazeta.uz/oz/2026/05/26/busine/)
- [CBU — asosiy stavka 14%](https://cbu.uz/uz/monetary-policy/publications/press-releases/3997757/)
- [Tashkent Times — tumanlarning 5 toifasi](https://www.tashkenttimes.uz/national/10316-uzbekistan-districts-and-cities-divided-into-5-categories-where-different-tax-incentives-and-subsidies-to-be-applied)
- [OECD — hududiy soliq imtiyozlari](https://www.oecd.org/en/publications/roadmap-for-sustainable-investment-policy-reforms-in-uzbekistan_20865f29-en/full-report/assessing-the-design-of-corporate-income-tax-incentives_cbaee226.html)
