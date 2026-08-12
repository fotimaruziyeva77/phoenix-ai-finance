"use client";

import { useLanguage } from "@/contexts/language-context";

const content = {
  en: {
    title: "Privacy Policy",
    lastUpdated: "Last updated: May 31, 2026",
    sections: [
      {
        heading: "1. Introduction",
        body: 'BotForge AI ("we", "us", "our") respects your privacy and is committed to protecting the personal data of our users ("you"). This Privacy Policy explains what data we collect, how we use it, and your rights regarding your information. This policy applies to all users of our platform worldwide.',
      },
      {
        heading: "2. Data We Collect",
        body: "We collect the following types of data: (a) Account information — name, email address, and password hash when you register; (b) Bot content — documents, knowledge base files, and bot configurations you upload; (c) Conversation data — messages between your bots and end-users; (d) Lead data — contact details and interaction data captured through your bots; (e) Usage data — page views, feature usage, and performance metrics; (f) Technical data — IP address, browser type, device information, collected automatically.",
      },
      {
        heading: "3. How We Use Your Data",
        body: "We use your data exclusively to: (a) provide and operate the BotForge AI platform; (b) process AI-powered chatbot conversations; (c) generate analytics and reports for your dashboard; (d) send essential service notifications (account verification, security alerts, billing); (e) improve the platform based on aggregated, anonymized usage patterns; (f) comply with legal obligations. We do NOT sell your personal data to third parties. We do NOT use your uploaded content to train AI models.",
      },
      {
        heading: "4. Data Storage & Security",
        body: "Your data is stored on secure cloud infrastructure with encryption at rest and in transit (TLS 1.2+). Sensitive data such as API tokens (e.g., Telegram bot tokens) are encrypted using AES-256 (Fernet) before storage. Passwords are hashed using Argon2. We implement access controls, audit logging, and regular security reviews to protect your data.",
      },
      {
        heading: "5. Third-Party Services",
        body: "We use the following third-party services: (a) Stripe — for payment processing (subject to Stripe's privacy policy); (b) Telegram API — for bot channel integration (when you connect Telegram); (c) OAuth providers (Google, GitHub) — for social sign-in (only basic profile data is received). These services process only the minimum data necessary for their function.",
      },
      {
        heading: "6. Cookies & Local Storage",
        body: "We use minimal browser storage: (a) an authentication token stored in localStorage for session management; (b) a language preference stored in localStorage. We do not use tracking cookies, advertising cookies, or third-party analytics trackers. No data is shared with advertising networks.",
      },
      {
        heading: "7. Data Retention",
        body: "We retain your data for as long as your account is active. Upon account deletion: (a) your personal data is removed within 30 days; (b) uploaded documents and bot configurations are permanently deleted; (c) conversation logs and lead data are permanently deleted; (d) anonymized, aggregated statistics may be retained for platform improvement. Billing records may be retained as required by tax and financial regulations.",
      },
      {
        heading: "8. Your Rights",
        body: "Regardless of your location, you have the right to: (a) Access — request a copy of the personal data we hold about you; (b) Correction — request correction of inaccurate data; (c) Deletion — request deletion of your account and associated data; (d) Data portability — request export of your data in a machine-readable format; (e) Restriction — request that we limit processing of your data; (f) Objection — object to processing of your data for specific purposes. To exercise any of these rights, contact us at support@botforge.ai.",
      },
      {
        heading: "9. International Data Transfers",
        body: "Our infrastructure may process data in multiple regions. When data is transferred across borders, we ensure appropriate safeguards are in place, including encryption in transit and compliance with applicable data protection regulations in the relevant jurisdictions.",
      },
      {
        heading: "10. Children's Privacy",
        body: "The Service is not directed to individuals under 18 years of age. We do not knowingly collect personal data from children. If you believe a child has provided us with personal data, please contact us and we will promptly delete it.",
      },
      {
        heading: "11. End-User Data (Your Customers)",
        body: "When visitors interact with your chatbots, we process their messages and any information they voluntarily provide (name, email, phone) on your behalf. You are the data controller for your end-users' data; we act as a data processor. You are responsible for informing your visitors about data collection through your bots and obtaining any necessary consent.",
      },
      {
        heading: "12. Changes to This Policy",
        body: "We may update this Privacy Policy from time to time. Material changes will be communicated via email or a prominent notice on our platform at least 14 days before they take effect. Continued use of the Service after changes constitutes acceptance.",
      },
      {
        heading: "13. Contact Us",
        body: "For privacy-related questions, data requests, or concerns, contact us at support@botforge.ai.",
      },
    ],
  },
  uz: {
    title: "Maxfiylik siyosati",
    lastUpdated: "Oxirgi yangilanish: 2026-yil 31-may",
    sections: [
      {
        heading: "1. Kirish",
        body: 'BotForge AI ("biz", "bizning") sizning maxfiyligingizni hurmat qiladi va foydalanuvchilarimizning shaxsiy ma\'lumotlarini himoya qilishga intiladi. Ushbu Maxfiylik siyosati biz qanday ma\'lumotlarni yig\'ishimiz, ulardan qanday foydalanishimiz va ma\'lumotlaringizga oid huquqlaringizni tushuntiradi. Ushbu siyosat butun dunyo bo\'ylab barcha foydalanuvchilarga taalluqlidir.',
      },
      {
        heading: "2. Yig'iladigan ma'lumotlar",
        body: "Biz quyidagi turdagi ma'lumotlarni yig'amiz: (a) Hisob ma'lumotlari — ro'yxatdan o'tishda ism, elektron pochta, parol xeshi; (b) Bot kontenti — yuklagan hujjatlar, bilimlar bazasi fayllari, bot sozlamalari; (c) Suhbat ma'lumotlari — botlaringiz va oxirgi foydalanuvchilar o'rtasidagi xabarlar; (d) Lid ma'lumotlari — botlaringiz orqali olingan aloqa ma'lumotlari; (e) Foydalanish ma'lumotlari — sahifa ko'rishlari va funksiya foydalanishi; (f) Texnik ma'lumotlar — IP manzil, brauzer turi, qurilma ma'lumotlari.",
      },
      {
        heading: "3. Ma'lumotlaringizdan qanday foydalanamiz",
        body: "Biz ma'lumotlaringizdan faqat quyidagi maqsadlarda foydalanamiz: (a) BotForge AI platformasini taqdim etish; (b) sun'iy intellektga asoslangan suhbatlarni qayta ishlash; (c) dashboard uchun tahlillar yaratish; (d) muhim xizmat bildirishnomalarini yuborish; (e) anonim foydalanish statistikasi asosida platformani yaxshilash; (f) qonuniy majburiyatlarga rioya qilish. Biz shaxsiy ma'lumotlaringizni uchinchi tomonlarga SOTMAYMIZ. Yuklagan kontentingizni AI modellarini o'qitish uchun ISHLATMAYMIZ.",
      },
      {
        heading: "4. Ma'lumotlarni saqlash va xavfsizlik",
        body: "Ma'lumotlaringiz saqlash vaqtida va uzatishda (TLS 1.2+) shifrlangan xavfsiz bulutli infratuzilmada saqlanadi. Maxfiy ma'lumotlar, masalan, API tokenlar, AES-256 (Fernet) yordamida saqlanishdan oldin shifrlanadi. Parollar Argon2 yordamida xeshlanadi. Biz kirish nazorati, audit jurnali va muntazam xavfsizlik ko'rikidan foydalanamiz.",
      },
      {
        heading: "5. Uchinchi tomon xizmatlari",
        body: "Biz quyidagi uchinchi tomon xizmatlaridan foydalanamiz: (a) Stripe — to'lovlarni qayta ishlash uchun; (b) Telegram API — bot kanali integratsiyasi uchun; (c) OAuth provayderlari (Google, GitHub) — ijtimoiy kirish uchun. Bu xizmatlar faqat funksiyalari uchun zarur bo'lgan minimal ma'lumotlarni qayta ishlaydi.",
      },
      {
        heading: "6. Cookie va mahalliy saqlash",
        body: "Biz minimal brauzer saqlashdan foydalanamiz: (a) sessiyani boshqarish uchun localStorage'da autentifikatsiya tokeni; (b) localStorage'da til sozlamasi. Biz kuzatish cookie'lari, reklama cookie'lari yoki uchinchi tomon tahlil kuzatuvchilaridan FOYDALANMAYMIZ. Hech qanday ma'lumot reklama tarmoqlari bilan baham ko'rilmaydi.",
      },
      {
        heading: "7. Ma'lumotlarni saqlash muddati",
        body: "Hisobingiz faol ekan, ma'lumotlaringizni saqlaymiz. Hisob o'chirilganda: (a) shaxsiy ma'lumotlaringiz 30 kun ichida o'chiriladi; (b) yuklangan hujjatlar va bot sozlamalari butunlay o'chiriladi; (c) suhbat jurnallari va lid ma'lumotlari butunlay o'chiriladi; (d) anonim, umumlashtirilgan statistika platforma yaxshilanishi uchun saqlanishi mumkin.",
      },
      {
        heading: "8. Sizning huquqlaringiz",
        body: "Joylashuvingizdan qat'iy nazar, sizda quyidagi huquqlar bor: (a) Kirish — biz saqlagan shaxsiy ma'lumotlaringiz nusxasini so'rash; (b) Tuzatish — noaniq ma'lumotlarni tuzatishni so'rash; (c) O'chirish — hisob va tegishli ma'lumotlarni o'chirishni so'rash; (d) Ma'lumotlar ko'chirilishi — ma'lumotlarni mashinada o'qilishi mumkin bo'lgan formatda eksport qilish; (e) Cheklash — ma'lumotlaringizni qayta ishlashni cheklash; (f) E'tiroz — muayyan maqsadlar uchun qayta ishlashga e'tiroz bildirish. Ushbu huquqlarni amalga oshirish uchun support@botforge.ai ga murojaat qiling.",
      },
      {
        heading: "9. Xalqaro ma'lumotlar uzatish",
        body: "Bizning infratuzilmamiz ma'lumotlarni bir nechta mintaqalarda qayta ishlashi mumkin. Ma'lumotlar chegara orqali uzatilganda, biz tegishli himoya vositalarini ta'minlaymiz, shu jumladan uzatish vaqtida shifrlash va tegishli yurisdiktsiyalardagi ma'lumotlarni himoya qilish qoidalariga muvofiqlik.",
      },
      {
        heading: "10. Bolalar maxfiyligi",
        body: "Xizmat 18 yoshdan kichik shaxslarga mo'ljallanmagan. Biz ataylab bolalardan shaxsiy ma'lumotlarni yig'maymiz. Agar bola bizga shaxsiy ma'lumotlar taqdim etganiga ishonsangiz, biz bilan bog'laning va biz ularni zudlik bilan o'chiramiz.",
      },
      {
        heading: "11. Oxirgi foydalanuvchi ma'lumotlari (sizning mijozlaringiz)",
        body: "Tashrif buyuruvchilar chatbotlaringiz bilan muloqot qilganda, biz ularning xabarlarini va ixtiyoriy ravishda taqdim etgan ma'lumotlarini sizning nomingizdan qayta ishlaymiz. Siz oxirgi foydalanuvchilaringiz ma'lumotlarining ma'lumotlar boshqaruvchisisiz; biz ma'lumotlarni qayta ishlovchi sifatida harakat qilamiz.",
      },
      {
        heading: "12. Siyosat o'zgarishlari",
        body: "Biz ushbu Maxfiylik siyosatini vaqti-vaqti bilan yangilashimiz mumkin. Muhim o'zgarishlar kuchga kirishidan kamida 14 kun oldin elektron pochta yoki platformadagi ko'zga ko'ringan bildirishnoma orqali xabar beriladi.",
      },
      {
        heading: "13. Biz bilan bog'lanish",
        body: "Maxfiylik bilan bog'liq savollar, ma'lumotlarga oid so'rovlar yoki tashvishlar uchun support@botforge.ai ga murojaat qiling.",
      },
    ],
  },
  ru: {
    title: "Политика конфиденциальности",
    lastUpdated: "Последнее обновление: 31 мая 2026 г.",
    sections: [
      {
        heading: "1. Введение",
        body: "BotForge AI («мы», «нас», «наш») уважает вашу конфиденциальность и стремится защитить персональные данные пользователей. Настоящая Политика объясняет, какие данные мы собираем, как используем и какие права у вас есть. Политика распространяется на всех пользователей платформы по всему миру.",
      },
      {
        heading: "2. Собираемые данные",
        body: "Мы собираем: (а) Данные аккаунта — имя, email, хеш пароля при регистрации; (б) Контент ботов — загруженные документы, файлы базы знаний, конфигурации; (в) Данные переписок — сообщения между ботами и конечными пользователями; (г) Данные лидов — контактная информация, полученная через ботов; (д) Данные использования — просмотры страниц, использование функций; (е) Технические данные — IP-адрес, тип браузера, информация об устройстве.",
      },
      {
        heading: "3. Как мы используем данные",
        body: "Мы используем данные исключительно для: (а) предоставления платформы BotForge AI; (б) обработки ИИ-переписок; (в) формирования аналитики; (г) отправки важных уведомлений; (д) улучшения платформы на основе обезличенной статистики; (е) выполнения юридических обязательств. Мы НЕ продаём персональные данные третьим лицам. Мы НЕ используем загруженный контент для обучения моделей ИИ.",
      },
      {
        heading: "4. Хранение и безопасность данных",
        body: "Данные хранятся на защищённой облачной инфраструктуре с шифрованием при хранении и передаче (TLS 1.2+). Конфиденциальные данные, такие как API-токены, шифруются AES-256 (Fernet). Пароли хешируются Argon2. Мы применяем контроль доступа, аудит-логирование и регулярные проверки безопасности.",
      },
      {
        heading: "5. Сторонние сервисы",
        body: "Мы используем: (а) Stripe — для обработки платежей; (б) Telegram API — для интеграции каналов; (в) OAuth-провайдеры (Google, GitHub) — для социального входа. Эти сервисы обрабатывают только минимально необходимые данные.",
      },
      {
        heading: "6. Cookies и локальное хранилище",
        body: "Мы используем минимальное хранилище браузера: (а) токен аутентификации в localStorage для управления сессией; (б) языковые настройки в localStorage. Мы НЕ используем рекламные cookie, отслеживающие cookie или сторонние трекеры аналитики. Никакие данные не передаются рекламным сетям.",
      },
      {
        heading: "7. Сроки хранения данных",
        body: "Мы храним данные, пока аккаунт активен. При удалении аккаунта: (а) персональные данные удаляются в течение 30 дней; (б) загруженные документы и конфигурации удаляются навсегда; (в) логи переписок и данные лидов удаляются; (г) обезличенная статистика может сохраняться для улучшения платформы.",
      },
      {
        heading: "8. Ваши права",
        body: "Независимо от местоположения, вы имеете право: (а) Доступ — запросить копию ваших данных; (б) Исправление — запросить исправление неточных данных; (в) Удаление — запросить удаление аккаунта и данных; (г) Переносимость — экспорт данных в машиночитаемом формате; (д) Ограничение — ограничить обработку данных; (е) Возражение — возразить против обработки. Для реализации прав обращайтесь на support@botforge.ai.",
      },
      {
        heading: "9. Международная передача данных",
        body: "Наша инфраструктура может обрабатывать данные в нескольких регионах. При трансграничной передаче мы обеспечиваем надлежащие меры защиты, включая шифрование при передаче и соответствие применимым нормам защиты данных.",
      },
      {
        heading: "10. Конфиденциальность детей",
        body: "Сервис не предназначен для лиц младше 18 лет. Мы не собираем сознательно данные детей. Если вы считаете, что ребёнок предоставил нам данные, свяжитесь с нами — мы незамедлительно удалим их.",
      },
      {
        heading: "11. Данные конечных пользователей (ваших клиентов)",
        body: "Когда посетители взаимодействуют с вашими ботами, мы обрабатываем их сообщения и добровольно предоставленные данные от вашего имени. Вы являетесь контролёром данных ваших пользователей; мы действуем как обработчик. Вы обязаны информировать посетителей о сборе данных и получить необходимое согласие.",
      },
      {
        heading: "12. Изменения политики",
        body: "Мы можем обновлять Политику. О существенных изменениях уведомим по email или заметным уведомлением на платформе минимум за 14 дней до вступления в силу.",
      },
      {
        heading: "13. Связаться с нами",
        body: "По вопросам конфиденциальности, запросам данных или жалобам обращайтесь на support@botforge.ai.",
      },
    ],
  },
};

export default function PrivacyPage() {
  const { lang } = useLanguage();
  const c = content[lang];

  return (
    <main className="bf-main--narrow" style={{ paddingBottom: "3rem" }}>
      <h1 style={{ marginTop: 0 }}>{c.title}</h1>
      <p style={{ color: "var(--bf-text-muted)", marginBottom: "2rem", fontSize: "0.875rem" }}>
        {c.lastUpdated}
      </p>
      {c.sections.map((s, i) => (
        <section key={i} style={{ marginBottom: "1.75rem" }}>
          <h2 style={{ fontSize: "1.125rem", marginBottom: "0.5rem" }}>{s.heading}</h2>
          <p style={{ color: "var(--bf-text-muted)", lineHeight: 1.7, margin: 0 }}>{s.body}</p>
        </section>
      ))}
    </main>
  );
}
