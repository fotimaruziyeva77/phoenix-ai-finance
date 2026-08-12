/**
 * Translations for the Phoenix AI finance advisor (uz / ru / en).
 *
 * Kept separate from `translations.ts` (the legacy 5.7k-line bundle) because this
 * surface is new, self-contained, and changes with the product pitch.
 *
 * **Engine messages.** `app/lib/finance` and `lib/finance/engine.ts` never build
 * user-facing sentences. They return `{ code, params }` pairs and the `msg()`
 * helper below renders them — that is what makes the verdict text translatable
 * instead of hard-coded Uzbek.
 */

export type FinanceLang = "uz" | "ru" | "en";

export const FINANCE_LANGS: readonly FinanceLang[] = ["uz", "ru", "en"];

export function asFinanceLang(value: string | undefined): FinanceLang {
  return value === "ru" || value === "en" ? value : "uz";
}

/* -------------------------------------------------------------- engine msgs */

export type MsgParams = Record<string, string | number>;
export type Msg = { code: string; params?: MsgParams };

const MESSAGES: Record<FinanceLang, Record<string, string>> = {
  uz: {
    // verdict reasons
    "reason.loss": "Rejalashtirilgan aylanmada oylik zarar: {amount} so'm. Doimiy xarajatlar yalpi foydadan yuqori.",
    "reason.overCapacity": "Zararsizlikka chiqish uchun quvvatingizning {util}% i kerak. Bu deyarli imkonsiz — bitta yomon oy zararga olib keladi.",
    "reason.tightCapacity": "Zararsizlik nuqtasi quvvatingizning {util}% i — zaxira kam. Aylanma biroz tushsa zararga o'tasiz.",
    "reason.slowPayback": "Zararsizlik bo'yicha muammo yo'q (quvvatning {util}% i), lekin kapital {months} oyda qoplanadi — bu juda sekin.",
    "reason.viable": "Zararsizlikka quvvatingizning {util}% ida chiqasiz — zaxira yetarli.",
    "reason.dailyCustomers": "Kuniga {count} ta mijoz (o'rtacha chek {check} so'm) — zararsizlik uchun shu kerak.",
    "reason.noPayback": "Sof foyda manfiy — boshlang'ich kapital qoplanmaydi.",
    "reason.longPayback": "Boshlang'ich kapital {months} oyda qoplanadi — bu juda uzoq.",
    "reason.payback": "Boshlang'ich kapital taxminan {months} oyda qoplanadi.",
    // recommendations
    "rec.reviewCosts": "Ijara yoki xodimlar sonini qayta ko'rib chiqing.",
    "rec.reduceCapital": "Boshlang'ich kapitalni kamaytiring yoki marjani oshiring.",
    "rec.taxRegime": "Soliq rejimi: \"{regime}\" eng arzoni — yiliga {amount} so'm tejaysiz.",
    "rec.rentHeavy": "Ijara doimiy xarajatlarning 40% dan ortig'ini tashkil qiladi — arzonroq joy sizni chegaradan chiqaradi.",
    "rec.preferentialSector": "Sohangiz davlat imtiyozli kredit dasturlariga kiradi — \"Kredit va imtiyozlar\" bo'limini tekshiring.",
    // credit load
    "load.safe": "Oylik to'lov aylanmangizning {pct}% ini oladi. Bu xavfsiz daraja.",
    "load.warning": "Oylik to'lov aylanmangizning {pct}% ini oladi. Bu chegara zona — daromad biroz tushsa to'lovda qiynalasiz.",
    "load.danger": "Oylik to'lov aylanmangizning {pct}% ini oladi. Bu xavfli zona — kredit summasini kamaytiring yoki muddatni uzaytiring.",
    "load.noRevenue": "Daromad kiritilmagan — kredit yukini baholab bo'lmaydi.",
    // tax regimes
    "regime.self_employed": "YaTT — aylanmadan 1%",
    "regime.turnover": "Aylanma solig'i — 4%",
    "regime.general": "Umumiy rejim — QQS 12% + foyda solig'i 15%",
    "regime.ineligible.overOneBillion": "Yillik aylanma 1 mlrd so'mdan oshadi",
    "regime.ineligible.notIndividual": "Faqat YaTT va o'zini o'zi band qilganlar uchun",
    "regime.ineligible.overFiveBillion": "Yillik aylanma 5 mlrd so'mdan oshadi",
    "tax.line.turnover1": "Aylanma solig'i (1%)",
    "tax.line.turnover4": "Aylanma solig'i (4%)",
    "tax.line.social": "Ijtimoiy soliq (12%)",
    "tax.line.vat": "QQS (12%, qo'shilgan qiymatdan)",
    "tax.line.profit": "Foyda solig'i (15%)",
    // verdict titles
    "verdict.viable": "Bu biznes ishlaydi",
    "verdict.tight": "Chegarada — ehtiyot bo'ling",
    "verdict.unprofitable": "Hozirgi shartlarda tavsiya etilmaydi",
    // advisor questions
    "ask.sector": "Qaysi sohada ishlaysiz? (masalan: oziq-ovqat do'koni, kafe, avtoservis)",
    "ask.location": "Qaysi shaharda? (Toshkent, Navoiy, Samarqand, Buxoro)",
    "ask.capital": "Boshlang'ich kapitalingiz qancha? (masalan: 150 mln)",
    "ask.employees": "Nechta xodim ishlaydi?",
    "ask.rent": "Oylik ijara qancha? (masalan: 8 mln)",
    "ask.principal": "Kredit summasi qancha? (masalan: 200 mln)",
    "ask.months": "Necha oyga? (masalan: 36)",
    "ask.rate": "Bank foizi necha foiz? (masalan: 28)",
    "ask.revenue": "Oylik aylanmangiz qancha? (masalan: 35 mln)",
    "ask.age": "Yoshingiz nechada?",
    "adv.unknown": "Aniqroq yozing: biznes-reja, kredit, soliq yoki imtiyozlar bo'yicha yordam bera olaman.",
    "adv.notNumber": "Raqam kiritilmadi. Iltimos, son bilan javob bering.",
    "adv.ready": "Rahmat. Hisobladim — natija quyida.",
    "adv.startPlan": "Biznes-rejani hisoblaymiz. Bir nechta savol beraman.",
    "adv.startCredit": "Kreditni tekshiramiz. Bir nechta savol beraman.",
    "adv.startTax": "Soliq rejimlarini solishtiramiz. Bir nechta savol beraman.",
    "adv.startBenefits": "Imtiyozlarni tekshiramiz. Bir nechta savol beraman.",
    // assumptions
    "assume.salary": "{city} bo'yicha o'rtacha oylik ish haqi",
    "assume.margin": "Soha yalpi marjasi",
    "assume.check": "O'rtacha chek",
    "assume.other": "Kommunal va sarf materiallari",
    "assume.capacity": "Bir xodim xizmat ko'rsata oladigan oylik aylanma",
  },
  ru: {
    "reason.loss": "При планируемом обороте месячный убыток: {amount} сум. Постоянные расходы выше валовой прибыли.",
    "reason.overCapacity": "Чтобы выйти в ноль, нужно {util}% вашей мощности. Это почти невозможно — один плохой месяц приведёт к убытку.",
    "reason.tightCapacity": "Точка безубыточности — {util}% мощности, запаса мало. Небольшое падение оборота уводит в минус.",
    "reason.slowPayback": "С безубыточностью проблем нет ({util}% мощности), но капитал окупится за {months} мес. — это слишком медленно.",
    "reason.viable": "Выходите в ноль на {util}% мощности — запас достаточный.",
    "reason.dailyCustomers": "{count} клиентов в день (средний чек {check} сум) — столько нужно для безубыточности.",
    "reason.noPayback": "Чистая прибыль отрицательная — стартовый капитал не окупится.",
    "reason.longPayback": "Стартовый капитал окупится за {months} мес. — это очень долго.",
    "reason.payback": "Стартовый капитал окупится примерно за {months} мес.",
    "rec.reviewCosts": "Пересмотрите аренду или количество сотрудников.",
    "rec.reduceCapital": "Уменьшите стартовый капитал или увеличьте маржу.",
    "rec.taxRegime": "Налоговый режим: «{regime}» дешевле всего — экономия {amount} сум в год.",
    "rec.rentHeavy": "Аренда составляет более 40% постоянных расходов — более дешёвое помещение выведет вас из зоны риска.",
    "rec.preferentialSector": "Ваша отрасль входит в государственные льготные кредитные программы — проверьте раздел «Кредит и льготы».",
    "load.safe": "Ежемесячный платёж съедает {pct}% оборота. Это безопасный уровень.",
    "load.warning": "Ежемесячный платёж съедает {pct}% оборота. Это пограничная зона — при падении дохода будет тяжело.",
    "load.danger": "Ежемесячный платёж съедает {pct}% оборота. Это опасная зона — уменьшите сумму кредита или увеличьте срок.",
    "load.noRevenue": "Доход не указан — оценить кредитную нагрузку невозможно.",
    "regime.self_employed": "ИП — 1% с оборота",
    "regime.turnover": "Налог с оборота — 4%",
    "regime.general": "Общий режим — НДС 12% + налог на прибыль 15%",
    "regime.ineligible.overOneBillion": "Годовой оборот превышает 1 млрд сум",
    "regime.ineligible.notIndividual": "Только для ИП и самозанятых",
    "regime.ineligible.overFiveBillion": "Годовой оборот превышает 5 млрд сум",
    "tax.line.turnover1": "Налог с оборота (1%)",
    "tax.line.turnover4": "Налог с оборота (4%)",
    "tax.line.social": "Социальный налог (12%)",
    "tax.line.vat": "НДС (12%, с добавленной стоимости)",
    "tax.line.profit": "Налог на прибыль (15%)",
    "verdict.viable": "Этот бизнес работает",
    "verdict.tight": "На грани — будьте осторожны",
    "verdict.unprofitable": "При текущих условиях не рекомендуется",
    // advisor questions
    "ask.sector": "В какой отрасли работаете? (например: продуктовый магазин, кафе, автосервис)",
    "ask.location": "В каком городе? (Ташкент, Навои, Самарканд, Бухара)",
    "ask.capital": "Какой у вас стартовый капитал? (например: 150 млн)",
    "ask.employees": "Сколько сотрудников?",
    "ask.rent": "Сколько стоит аренда в месяц? (например: 8 млн)",
    "ask.principal": "Какая сумма кредита? (например: 200 млн)",
    "ask.months": "На сколько месяцев? (например: 36)",
    "ask.rate": "Какая ставка банка? (например: 28)",
    "ask.revenue": "Какой у вас оборот в месяц? (например: 35 млн)",
    "ask.age": "Сколько вам лет?",
    "adv.unknown": "Уточните запрос: могу помочь с бизнес-планом, кредитом, налогами или льготами.",
    "adv.notNumber": "Не вижу числа. Пожалуйста, ответьте цифрой.",
    "adv.ready": "Спасибо. Расчёт готов — результат ниже.",
    "adv.startPlan": "Посчитаем бизнес-план. Задам несколько вопросов.",
    "adv.startCredit": "Проверим кредит. Задам несколько вопросов.",
    "adv.startTax": "Сравним налоговые режимы. Задам несколько вопросов.",
    "adv.startBenefits": "Проверим льготы. Задам несколько вопросов.",
    "assume.salary": "Средняя месячная зарплата — {city}",
    "assume.margin": "Валовая маржа отрасли",
    "assume.check": "Средний чек",
    "assume.other": "Коммунальные услуги и расходники",
    "assume.capacity": "Оборот, который обслуживает один сотрудник в месяц",
  },
  en: {
    "reason.loss": "At the planned revenue you lose {amount} so'm a month. Fixed costs exceed gross profit.",
    "reason.overCapacity": "Breaking even needs {util}% of your capacity. That is close to impossible — one bad month puts you under.",
    "reason.tightCapacity": "Break-even sits at {util}% of capacity — little headroom. A small dip in revenue turns into a loss.",
    "reason.slowPayback": "Break-even is fine ({util}% of capacity), but the capital takes {months} months to return — too slow.",
    "reason.viable": "You break even at {util}% of capacity — comfortable headroom.",
    "reason.dailyCustomers": "{count} customers a day (average sale {check} so'm) — that is what break-even requires.",
    "reason.noPayback": "Net profit is negative — the starting capital never returns.",
    "reason.longPayback": "The starting capital takes {months} months to return — that is very long.",
    "reason.payback": "The starting capital returns in roughly {months} months.",
    "rec.reviewCosts": "Reconsider the rent or the headcount.",
    "rec.reduceCapital": "Lower the starting capital or raise the margin.",
    "rec.taxRegime": "Tax regime: \"{regime}\" is cheapest — it saves {amount} so'm a year.",
    "rec.rentHeavy": "Rent is over 40% of fixed costs — a cheaper location moves you out of the danger zone.",
    "rec.preferentialSector": "Your sector qualifies for state preferential loan programmes — check the Credit & benefits section.",
    "load.safe": "The monthly payment takes {pct}% of your revenue. That is a safe level.",
    "load.warning": "The monthly payment takes {pct}% of your revenue. Borderline — a small dip makes repayment hard.",
    "load.danger": "The monthly payment takes {pct}% of your revenue. Dangerous — reduce the amount or extend the term.",
    "load.noRevenue": "No revenue entered — the credit load cannot be assessed.",
    "regime.self_employed": "Sole trader — 1% of turnover",
    "regime.turnover": "Turnover tax — 4%",
    "regime.general": "General regime — 12% VAT + 15% profit tax",
    "regime.ineligible.overOneBillion": "Annual turnover exceeds 1 bln so'm",
    "regime.ineligible.notIndividual": "Sole traders and self-employed only",
    "regime.ineligible.overFiveBillion": "Annual turnover exceeds 5 bln so'm",
    "tax.line.turnover1": "Turnover tax (1%)",
    "tax.line.turnover4": "Turnover tax (4%)",
    "tax.line.social": "Social tax (12%)",
    "tax.line.vat": "VAT (12%, on value added)",
    "tax.line.profit": "Profit tax (15%)",
    "verdict.viable": "This business works",
    "verdict.tight": "Borderline — proceed carefully",
    "verdict.unprofitable": "Not advisable on these terms",
    // advisor questions
    "ask.sector": "Which sector are you in? (e.g. grocery store, cafe, auto service)",
    "ask.location": "Which city? (Tashkent, Navoi, Samarkand, Bukhara)",
    "ask.capital": "How much starting capital? (e.g. 150 mln)",
    "ask.employees": "How many employees?",
    "ask.rent": "What is the monthly rent? (e.g. 8 mln)",
    "ask.principal": "How much is the loan? (e.g. 200 mln)",
    "ask.months": "Over how many months? (e.g. 36)",
    "ask.rate": "What rate does the bank offer? (e.g. 28)",
    "ask.revenue": "What is your monthly revenue? (e.g. 35 mln)",
    "ask.age": "How old are you?",
    "adv.unknown": "Could you be more specific? I can help with a business plan, credit, tax or benefits.",
    "adv.notNumber": "I could not read a number there. Please answer with digits.",
    "adv.ready": "Thanks. Calculated — the result is below.",
    "adv.startPlan": "Let's work out the business plan. A few questions first.",
    "adv.startCredit": "Let's check the loan. A few questions first.",
    "adv.startTax": "Let's compare the tax regimes. A few questions first.",
    "adv.startBenefits": "Let's check your benefits. A few questions first.",
    "assume.salary": "Average monthly wage in {city}",
    "assume.margin": "Sector gross margin",
    "assume.check": "Average sale",
    "assume.other": "Utilities and consumables",
    "assume.capacity": "Monthly revenue one employee can service",
  },
};

/** Render an engine message. Unknown codes fall back to the code itself. */
export function msg(m: Msg, lang: FinanceLang): string {
  const template = MESSAGES[lang][m.code] ?? MESSAGES.uz[m.code] ?? m.code;
  if (!m.params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    String(m.params?.[key] ?? `{${key}}`),
  );
}

/* ------------------------------------------------------------------ sectors */

export const SECTOR_LABELS: Record<FinanceLang, Record<string, string>> = {
  uz: {
    oziq_ovqat: "Oziq-ovqat do'koni",
    kafe: "Kafe / oshxona",
    nonvoyxona: "Nonvoyxona",
    kiyim: "Kiyim do'koni",
    gozallik: "Go'zallik saloni",
    avtoservis: "Avtoservis",
    chorvachilik: "Chorvachilik",
    parrandachilik: "Parrandachilik",
    it_xizmat: "IT / raqamli xizmat",
    yuk_tashish: "Yuk tashish / dostavka",
  },
  ru: {
    oziq_ovqat: "Продуктовый магазин",
    kafe: "Кафе / столовая",
    nonvoyxona: "Пекарня",
    kiyim: "Магазин одежды",
    gozallik: "Салон красоты",
    avtoservis: "Автосервис",
    chorvachilik: "Животноводство",
    parrandachilik: "Птицеводство",
    it_xizmat: "IT / цифровые услуги",
    yuk_tashish: "Грузоперевозки / доставка",
  },
  en: {
    oziq_ovqat: "Grocery store",
    kafe: "Cafe",
    nonvoyxona: "Bakery",
    kiyim: "Clothing store",
    gozallik: "Beauty salon",
    avtoservis: "Auto service",
    chorvachilik: "Livestock",
    parrandachilik: "Poultry",
    it_xizmat: "IT services",
    yuk_tashish: "Delivery / logistics",
  },
};

export const LOCATION_LABELS: Record<FinanceLang, Record<string, string>> = {
  uz: {
    toshkent: "Toshkent shahri",
    navoiy: "Navoiy shahri",
    samarqand: "Samarqand shahri",
    buxoro: "Buxoro shahri",
  },
  ru: {
    toshkent: "город Ташкент",
    navoiy: "город Навои",
    samarqand: "город Самарканд",
    buxoro: "город Бухара",
  },
  en: {
    toshkent: "Tashkent city",
    navoiy: "Navoi city",
    samarqand: "Samarkand city",
    buxoro: "Bukhara city",
  },
};

export const sectorLabel = (id: string, lang: FinanceLang) =>
  SECTOR_LABELS[lang][id] ?? SECTOR_LABELS.uz[id] ?? id;

export const locationLabel = (id: string, lang: FinanceLang) =>
  LOCATION_LABELS[lang][id] ?? LOCATION_LABELS.uz[id] ?? id;

/* ---------------------------------------------------------------- UI copy */

export type FinanceCopy = (typeof COPY)["uz"];

export const COPY = {
  uz: {
    brandTagline: "G'oyadan — o'sishgacha",
    currency: "so'm",
    perMonth: "so'm/oy",
    perYear: "so'm/yil",
    months: "oy",
    people: "ta",
    free: "Shaxsiy kabinet · barcha asboblar bitta profilda",
    sourcesAsOf: "Ma'lumot 2026-yil 12-avgust holatiga",
    back: "← Bosh sahifa",
    unverified: "tasdiqlanishi kerak",
    tools: {
      plan: "Biznes-reja",
      credit: "Kredit va imtiyozlar",
      tax: "Soliq",
      chat: "Maslahatchi",
    },
    landing: {
      eyebrow: "Kichik tadbirkorlar uchun AI moliyaviy maslahatchi",
      titleA: "Buxgalter yollay olmaysizmi?",
      titleB: "Unda bu sizning o'rningizga hisoblaydi.",
      subtitle:
        "Biznes-reja, kredit, soliq va lokatsiya — to'rttasi bitta joyda. Raqamlar aniq, javob 30 soniyada, til tushunarli.",
      ctaPrimary: "Biznes-rejani hisoblash",
      ctaSecondary: "Imtiyozimni tekshirish",
      statLabel: "Tadbirkor ko'rmaydigan farq",
      statCaption:
        "Bir xil {amount} so'mlik kredit, {months} oyga: {best}% da olsangiz {market}% ga nisbatan shuncha tejaysiz. Tadbirkor bu farqni ko'rmaydi — chunki u bitta bankka boradi.",
      statSource: "Foiz stavkalari: bank.uz, 2026-yil 12-avgust. Hisob shu sahifada real vaqtda bajarildi.",
      trustA: "Hisobni AI emas, matematik kod bajaradi",
      trustB: "Har bir raqamda manba va sana",
      trustC: "Taxminlar ochiq va tahrirlanadi",
      painTitle: "Muammo qulaylikda emas — pulda",
      painSub:
        "Kichik tadbirkor buxgalter yoki konsultant yollay olmaydi. Shuning uchun moliyaviy qarorlarni ko'r-ko'rona qabul qiladi. Va bu qarorlar unga haqiqiy pulga tushadi.",
      pains: [
        {
          title: "Noto'g'ri soliq rejimi",
          text: "Ro'yxatdan o'tishda tanlangan rejim noto'g'ri bo'lsa, har oy ortiqcha to'laysiz. Yil oxirida ham bilmaysiz — zarar ko'rinmaydi, shuning uchun hech kim tuzatmaydi.",
        },
        {
          title: "Ko'tara olmaydigan kredit",
          text: "Bank oylik to'lovni ko'rsatadi. Lekin \"sizning biznesingiz buni ko'taradimi?\" degan savolga javob bermaydi — bu uning ishi emas.",
        },
        {
          title: "Bilmagan imtiyozingiz",
          text: "Yoshingiz, sohangiz yoki hududingiz sababli imtiyozli dasturga loyiq bo'lishingiz mumkin. Bank buni aytmaydi — u o'z mahsulotini sotadi.",
        },
      ],
      featTitle: "Nima qila olamiz",
      featSub: "To'rtta asbob, bitta biznes profili. Bir marta kiritasiz — hammasi ishlaydi.",
      feats: [
        { title: "Biznes-reja", text: "Zararsizlik nuqtasi, kuniga kerakli mijoz soni, qoplanish muddati. Oxirida aniq hukm: ishlaydi, chegarada yoki tavsiya etilmaydi." },
        { title: "Kredit va imtiyozlar", text: "Kredit yuki — aylanmangizning necha foizini yeydi. Va siz haqli bo'lgan, lekin bilmagan davlat imtiyozli dasturlari." },
        { title: "Soliq hisob-kitobi", text: "2026-yil rejimlarini solishtiramiz va eng arzonini tanlaymiz. Noto'g'ri rejim yiliga qancha turishini raqamda ko'rasiz." },
        { title: "Lokatsiya tahlili", text: "Bir xil biznes Toshkentda va Navoiyda boshqacha natija beradi. Shaharni almashtiring — hukm o'zgarganini ko'ring." },
      ],
      trustTitle: "Nega bizga ishonish mumkin",
      trustSub: "Chunki bizning daromadimiz sizning kreditingizga bog'liq emas.",
      contrast: [
        { who: "Bank", says: "“Sizga kredit bera olamiz. Oylik to'lov shuncha.”" },
        { who: "Kreditlash platformasi", says: "“Arizangizni bir nechta bankka yuboramiz.”" },
        { who: "Phoenix AI", says: "“Bu kreditni olmang — aylanmangizning 31% ini yeydi. Avval ijarani tushiring.”" },
      ],
      stepsTitle: "Qanday ishlaydi",
      steps: [
        { title: "Biznesingizni bir marta kiriting", text: "Soha, shahar, kapital, xodim, ijara — 8 ta savol. Boshqa hech qachon qayta so'ramaymiz." },
        { title: "Raqamlar avtomatik hisoblanadi", text: "Hisob-kitobni sun'iy intellekt emas, matematik kod bajaradi. Xato bo'lishi mumkin emas." },
        { title: "Aniq javob olasiz", text: "“Ishlaydi”, “chegarada” yoki “tavsiya etilmaydi” — sabablari bilan birga." },
        { title: "Nima qilishni bilasiz", text: "Qaysi soliq rejimi, qaysi shahar, qanday kredit — har biri uchun aniq tavsiya." },
      ],
      finalTitle: "Biznesingiz foyda beradimi?",
      finalText: "Kirish bir daqiqa oladi — hisob-kitob 30 soniyada tayyor.",
      finalCta: "Hisoblashni boshlash",
      disclaimer:
        "Ogohlantirish: platforma ma'lumot va rejalashtirish uchun mo'ljallangan, litsenziyalangan moliyaviy yoki soliq maslahati emas. Soliq stavkalari va bank shartlari ochiq manbalardan olingan (2026-yil 12-avgust) va o'zgarishi mumkin. Yakuniy qaror qabul qilishdan oldin buxgalter yoki bank bilan tasdiqlang. Biz aniq bankni tavsiya qilmaymiz — faqat ochiq ma'lumotni solishtiramiz.",
    },
    plan: {
      title: "Biznesingiz foyda beradimi?",
      subtitle:
        "Ma'lumotlarni kiriting — zararsizlik nuqtasi, qoplanish muddati, eng arzon soliq rejimi va shaharlar taqqoslashini darhol ko'rasiz.",
      formTitle: "Biznesingiz haqida",
      formHint: "8 ta savol — javob 30 soniyada tayyor.",
      f: {
        name: "Biznes nomi",
        sector: "Biznes turi",
        location: "Shahar / lokatsiya",
        capital: "Boshlang'ich kapital",
        employees: "Xodimlar soni",
        rent: "Oylik ijara (so'm)",
        product: "Mahsulot / xizmat",
        goal: "Maqsad",
      },
      submit: "Hisoblash",
      nameRequired: "Biznes nomini kiriting.",
      empty: "Ma'lumotlarni kiriting — biznesingiz foyda beradimi yoki yo'qligini aniq aytamiz.",
      m: {
        breakEven: "Zararsizlik nuqtasi",
        daily: "Kuniga kerakli mijoz",
        profit: "Oylik sof foyda",
        payback: "Qoplanish muddati",
        util: "Quvvat bandligi",
        fixed: "Doimiy xarajat",
      },
      compareTitle: "Lokatsiya taqqoslash",
      compareDiffer: "{bestCity}: {bestVerdict}. {otherCity}: {otherVerdict}. Bir xil biznes, boshqa shahar — natija boshqacha.",
      compareSame: "Har ikkala shaharda ham natija bir xil: {bestVerdict}. Eng tez qoplanish: {bestCity}.",
      best: "eng yaxshi",
      cmp: {
        breakEven: "Zararsizlik",
        daily: "Kuniga mijoz",
        profit: "Oylik sof foyda",
        payback: "Qoplanish",
        salary: "Ish haqi (taxminiy)",
        noPayback: "qoplanmaydi",
      },
      taxTitle: "Qaysi soliq rejimi arzon?",
      taxBest: "Eng arzon rejim — {regime}. Noto'g'ri rejim sizga yiliga {amount} so'm qimmatga tushadi.",
      recTitle: "Nima qilish kerak",
      assumeTitle: "Hisobda ishlatilgan taxminlar",
      assumeNote:
        "Bu raqamlar rejalashtirish uchun taxminiy ko'rsatkichlar. O'z raqamlaringiz boshqacha bo'lsa, natija ham o'zgaradi — hech narsa yashirilmagan.",
      disclaimer:
        "Hisob-kitob rejalashtirish uchun mo'ljallangan va litsenziyalangan moliyaviy yoki soliq maslahati emas. Soliq stavkalari 2026-yil 12-avgust holatiga ochiq manbalardan olingan. Yakuniy qaror qabul qilishdan oldin buxgalter bilan tasdiqlang.",
    },
    credit: {
      title: "Bu kreditni ko'tara olasizmi?",
      subtitle:
        "Imzolashdan oldin bilib oling. Oylik to'lov, kredit yuki, banklar solishtiruvi va siz haqli bo'lgan imtiyozli dasturlar.",
      formTitle: "Kredit va imtiyozlar",
      formHint: "Bank taklifini kiriting — arzonroq yo'l bor-yo'qligini tekshiramiz.",
      f: {
        principal: "Kredit summasi (so'm)",
        months: "Muddat (oy)",
        rate: "Bank foizi (%)",
        revenue: "Oylik aylanmangiz (so'm)",
        age: "Yoshingiz",
        sector: "Soha",
        priorLoan: "Avval mikroqarz olganman (kredit tarixim toza)",
        collateral: "Garovim bor",
      },
      submit: "Tekshirish",
      invalid: "Kredit summasi va muddatini kiriting.",
      empty: "Bank taklifingizni kiriting — imtiyozli dastur bor-yo'qligini va bu kreditni ko'tara olishingizni aytamiz.",
      headlineLabel: "Siz bilmagan imtiyoz",
      headlineCaption:
        "{program} dasturi orqali {rate}% da olsangiz, {entered}% ga nisbatan shuncha tejaysiz. Oylik to'lov {before} → {after} so'm.",
      m: {
        monthly: "Oylik to'lov",
        total: "Jami to'lov",
        interest: "Ortiqcha to'lov",
        overpay: "Ortiqcha to'lov ulushi",
      },
      programsTitle: "Sizga tegishli imtiyozli dasturlar",
      programsHint: "Yosh, soha, kredit tarixi va garov holatingiz bo'yicha moslashtirildi.",
      noPrograms:
        "Kiritilgan ma'lumotlar bo'yicha mos dastur topilmadi. Yosh, soha yoki kredit tarixi o'zgarsa natija ham o'zgaradi.",
      forWhom: "Kimga",
      saving: "Tejash",
      source: "Manba",
      link: "havola",
      banksTitle: "Banklar taqqoslash",
      banksHint: "Ochiq e'lon qilingan takliflar. Biz bank tavsiya qilmaymiz — faqat solishtiramiz, tanlov sizniki.",
      th: { bank: "Bank", rate: "Foiz", term: "Muddat", max: "Maks." },
      years: "yil",
      banksNote:
        "Manba: bank.uz, 2026-yil 12-avgust holatiga. Foiz stavkalari o'zgaradi — yakuniy shartlarni bank bilan tasdiqlang. Bu ro'yxat reklama yoki tavsiya emas, ochiq ma'lumot solishtiruvi.",
      disclaimer:
        "Hisob-kitob rejalashtirish uchun mo'ljallangan va litsenziyalangan moliyaviy maslahat emas. Bank shartlari va imtiyozli dastur mezonlari ochiq manbalardan olingan (2026-yil 12-avgust) va o'zgarishi mumkin. Biz aniq bankni tavsiya qilmaymiz.",
    },
    tax: {
      title: "Siz ortiqcha soliq to'layapsizmi?",
      subtitle:
        "2026-yil rejimlarini solishtiramiz. Noto'g'ri rejim har oy pul yeydi — va bu zarar hisobotda ko'rinmaydi.",
      formTitle: "Soliq hisob-kitobi",
      formHint: "2026-yil rejimlarini solishtiramiz va eng arzonini topamiz.",
      f: {
        revenue: "Oylik aylanma (so'm)",
        sector: "Soha",
        employees: "Xodimlar soni",
        salary: "O'rtacha oylik",
        rent: "Oylik ijara va boshqa xarajat",
        individual: "Men YaTT / o'zini o'zi band qilganman",
      },
      submit: "Hisoblash",
      empty: "Aylanmangizni kiriting — qaysi rejim arzon ekanini va noto'g'ri rejim yiliga qancha turishini ko'rsatamiz.",
      headlineLabel: "Noto'g'ri rejim sizga qancha turadi",
      headlineCaption:
        "Har yili. Eng arzon rejim — {regime}. Ko'p tadbirkor buni bilmaydi, chunki zarar ko'rinmaydi — u shunchaki har oy hisobdan chiqib ketadi.",
      warnOverOneBillion:
        "Yillik aylanmangiz 1 mlrd so'mdan oshdi — YaTT uchun 1% li imtiyozli stavka endi qo'llanmaydi.",
      warnOverFiveBillion:
        "Yillik aylanmangiz 5 mlrd so'mdan oshdi — umumiy soliq rejimiga (QQS + foyda solig'i) o'tish majburiy bo'ladi.",
      compareTitle: "Rejimlar taqqoslash",
      annualRevenue: "Yillik aylanma",
      cheapest: "eng arzon",
      monthlyIs: "Oyiga {amount} so'm · aylanmaning {pct}% i",
      notEligible: "Mos emas",
      disclaimer:
        "Bu hisob-kitob taxminiy: QQS qo'shilgan qiymatning 12% i, foyda solig'i operatsion foydaning 15% i sifatida modellashtirilgan. Haqiqiy hisobotda kirish QQS hisobga olinishi, chegiriladigan xarajatlar qoidalari va soha imtiyozlari bor. Buxgalter yoki soliq.uz orqali tasdiqlang.",
      engineDisclaimer:
        "Bu hisob-kitob taxminiy va rejalashtirish uchun mo'ljallangan. Stavkalar 2026-yil 12-avgust holatiga ochiq manbalardan olingan. Yakuniy qaror qabul qilishdan oldin buxgalter yoki soliq.uz orqali tasdiqlang.",
    },
    ai: {
      button: "AI maslahati",
      loadingButton: "Tayyorlanmoqda…",
      title: "AI maslahati",
      subtitle: "Gemini raqamlaringizni tushuntiradi — hisob-kitob o'zgarmaydi",
      loading: "Maslahat tayyorlanmoqda…",
      unavailable: "AI maslahatchi hozircha javob bermadi. Raqamlar yuqorida — ular AI'siz, aniq hisoblangan.",
      note: "Raqamlar deterministik kodda hisoblangan; AI faqat tushuntiradi. Bu litsenziyalangan moliyaviy maslahat emas.",
      close: "Yopish",
    },
    chat: {
      title: "Moliyaviy maslahatchi",
      subtitle:
        "Savolingizni yozing yoki tayyor savollardan tanlang. Maslahatchi kerakli ma'lumotni so'raydi va hisobni o'zi bajaradi.",
      placeholder: "Masalan: Navoiyda kafe ochsam bo'ladimi?",
      send: "Yuborish",
      restart: "Boshidan",
      greeting:
        "Assalomu alaykum! Men Phoenix AI maslahatchisiman. Biznes-reja, kredit, soliq va imtiyozlar bo'yicha yordam beraman. Nima qilmoqchisiz?",
      suggestions: [
        "Biznesim foyda beradimi?",
        "Bu kreditni ko'tara olamanmi?",
        "Qaysi soliq rejimi arzon?",
        "Menga qanday imtiyoz bor?",
      ],
      thinking: "Hisoblayapman…",
      engineNote:
        "Maslahatchi javoblari yuqoridagi kalkulyatorlarning aynan o'zi bilan hisoblanadi — raqamlar taxmin qilinmaydi.",
      openTool: "To'liq sahifada ochish",
    },
  },

  ru: {
    brandTagline: "От идеи — к росту",
    currency: "сум",
    perMonth: "сум/мес",
    perYear: "сум/год",
    months: "мес.",
    people: "",
    free: "Личный кабинет · все инструменты в одном профиле",
    sourcesAsOf: "Данные на 12 августа 2026 года",
    back: "← На главную",
    unverified: "требует подтверждения",
    tools: {
      plan: "Бизнес-план",
      credit: "Кредит и льготы",
      tax: "Налоги",
      chat: "Советник",
    },
    landing: {
      eyebrow: "AI-финансовый советник для малого бизнеса",
      titleA: "Не можете нанять бухгалтера?",
      titleB: "Тогда это посчитает за вас.",
      subtitle:
        "Бизнес-план, кредит, налоги и локация — всё в одном месте. Точные цифры, ответ за 30 секунд, понятный язык.",
      ctaPrimary: "Рассчитать бизнес-план",
      ctaSecondary: "Проверить мои льготы",
      statLabel: "Разница, которую предприниматель не видит",
      statCaption:
        "Один и тот же кредит {amount} сум на {months} мес.: под {best}% вы сэкономите столько по сравнению с {market}%. Предприниматель этой разницы не видит — он идёт в один банк.",
      statSource: "Ставки: bank.uz, 12 августа 2026 г. Расчёт выполнен на этой странице в реальном времени.",
      trustA: "Считает математический код, а не ИИ",
      trustB: "У каждой цифры есть источник и дата",
      trustC: "Все допущения открыты и редактируются",
      painTitle: "Проблема не в удобстве — в деньгах",
      painSub:
        "Малый предприниматель не может нанять бухгалтера или консультанта. Поэтому финансовые решения он принимает вслепую. И эти решения стоят ему реальных денег.",
      pains: [
        { title: "Неверный налоговый режим", text: "Если режим при регистрации выбран неверно, вы переплачиваете каждый месяц. И к концу года не узнаете — убыток не виден, поэтому никто его не исправляет." },
        { title: "Непосильный кредит", text: "Банк показывает ежемесячный платёж. Но на вопрос «потянет ли это ваш бизнес?» он не отвечает — это не его работа." },
        { title: "Льгота, о которой вы не знаете", text: "По возрасту, отрасли или региону вы можете подходить под льготную программу. Банк об этом не скажет — он продаёт свой продукт." },
      ],
      featTitle: "Что мы умеем",
      featSub: "Четыре инструмента, один профиль бизнеса. Вводите один раз — работает везде.",
      feats: [
        { title: "Бизнес-план", text: "Точка безубыточности, сколько клиентов нужно в день, срок окупаемости. В конце — чёткий вердикт." },
        { title: "Кредит и льготы", text: "Кредитная нагрузка — какую долю оборота съедает платёж. И государственные льготные программы, на которые вы имеете право." },
        { title: "Расчёт налогов", text: "Сравниваем режимы 2026 года и выбираем самый дешёвый. Вы видите в цифрах, сколько стоит неверный режим." },
        { title: "Анализ локации", text: "Один и тот же бизнес в Ташкенте и Навои даёт разный результат. Поменяйте город — вердикт изменится." },
      ],
      trustTitle: "Почему нам можно доверять",
      trustSub: "Потому что наш доход не зависит от вашего кредита.",
      contrast: [
        { who: "Банк", says: "«Мы можем выдать вам кредит. Платёж такой-то.»" },
        { who: "Кредитная платформа", says: "«Отправим вашу заявку в несколько банков.»" },
        { who: "Phoenix AI", says: "«Не берите этот кредит — он съест 31% оборота. Сначала снизьте аренду.»" },
      ],
      stepsTitle: "Как это работает",
      steps: [
        { title: "Введите данные о бизнесе один раз", text: "Отрасль, город, капитал, сотрудники, аренда — 8 вопросов. Больше не спросим." },
        { title: "Цифры считаются автоматически", text: "Расчёт выполняет математический код, а не ИИ. Ошибка невозможна." },
        { title: "Вы получаете чёткий ответ", text: "«Работает», «на грани» или «не рекомендуется» — вместе с причинами." },
        { title: "Вы знаете, что делать", text: "Какой налоговый режим, какой город, какой кредит — по каждому пункту конкретная рекомендация." },
      ],
      finalTitle: "Будет ли ваш бизнес прибыльным?",
      finalText: "Вход занимает минуту — расчёт готов за 30 секунд.",
      finalCta: "Начать расчёт",
      disclaimer:
        "Предупреждение: платформа предназначена для информирования и планирования и не является лицензированной финансовой или налоговой консультацией. Налоговые ставки и условия банков взяты из открытых источников (12 августа 2026 г.) и могут измениться. Перед принятием решения подтвердите данные у бухгалтера или в банке. Мы не рекомендуем конкретный банк — только сравниваем открытые данные.",
    },
    plan: {
      title: "Будет ли ваш бизнес прибыльным?",
      subtitle:
        "Введите данные — сразу увидите точку безубыточности, срок окупаемости, самый дешёвый налоговый режим и сравнение городов.",
      formTitle: "О вашем бизнесе",
      formHint: "8 вопросов — ответ за 30 секунд.",
      f: {
        name: "Название бизнеса",
        sector: "Тип бизнеса",
        location: "Город / локация",
        capital: "Стартовый капитал",
        employees: "Количество сотрудников",
        rent: "Аренда в месяц (сум)",
        product: "Товар / услуга",
        goal: "Цель",
      },
      submit: "Рассчитать",
      nameRequired: "Введите название бизнеса.",
      empty: "Введите данные — мы точно скажем, будет ли бизнес прибыльным.",
      m: {
        breakEven: "Точка безубыточности",
        daily: "Клиентов в день",
        profit: "Чистая прибыль в месяц",
        payback: "Срок окупаемости",
        util: "Загрузка мощности",
        fixed: "Постоянные расходы",
      },
      compareTitle: "Сравнение локаций",
      compareDiffer: "{bestCity}: {bestVerdict}. {otherCity}: {otherVerdict}. Тот же бизнес, другой город — другой результат.",
      compareSame: "В обоих городах результат одинаковый: {bestVerdict}. Быстрее всего окупается: {bestCity}.",
      best: "лучший вариант",
      cmp: {
        breakEven: "Безубыточность",
        daily: "Клиентов в день",
        profit: "Чистая прибыль",
        payback: "Окупаемость",
        salary: "Зарплата (оценка)",
        noPayback: "не окупается",
      },
      taxTitle: "Какой налоговый режим дешевле?",
      taxBest: "Самый дешёвый режим — {regime}. Неверный режим обходится вам в {amount} сум в год.",
      recTitle: "Что делать",
      assumeTitle: "Допущения, использованные в расчёте",
      assumeNote:
        "Это ориентировочные показатели для планирования. Если ваши цифры другие — изменится и результат. Ничего не скрыто.",
      disclaimer:
        "Расчёт предназначен для планирования и не является лицензированной финансовой или налоговой консультацией. Ставки взяты из открытых источников на 12 августа 2026 г. Подтвердите у бухгалтера.",
    },
    credit: {
      title: "Потянете ли вы этот кредит?",
      subtitle:
        "Узнайте до подписания. Платёж, кредитная нагрузка, сравнение банков и льготные программы, на которые вы имеете право.",
      formTitle: "Кредит и льготы",
      formHint: "Введите предложение банка — проверим, есть ли вариант дешевле.",
      f: {
        principal: "Сумма кредита (сум)",
        months: "Срок (мес.)",
        rate: "Ставка банка (%)",
        revenue: "Ваш оборот в месяц (сум)",
        age: "Ваш возраст",
        sector: "Отрасль",
        priorLoan: "Ранее брал микрозайм (кредитная история чистая)",
        collateral: "У меня есть залог",
      },
      submit: "Проверить",
      invalid: "Укажите сумму кредита и срок.",
      empty: "Введите предложение банка — скажем, есть ли льготная программа и потянете ли вы этот кредит.",
      headlineLabel: "Льгота, о которой вы не знали",
      headlineCaption:
        "По программе «{program}» под {rate}% вы сэкономите столько по сравнению с {entered}%. Платёж {before} → {after} сум.",
      m: {
        monthly: "Платёж в месяц",
        total: "Всего к выплате",
        interest: "Переплата",
        overpay: "Доля переплаты",
      },
      programsTitle: "Подходящие вам льготные программы",
      programsHint: "Подобрано по возрасту, отрасли, кредитной истории и наличию залога.",
      noPrograms:
        "По указанным данным подходящих программ не найдено. Если изменится возраст, отрасль или кредитная история — изменится и результат.",
      forWhom: "Кому",
      saving: "Экономия",
      source: "Источник",
      link: "ссылка",
      banksTitle: "Сравнение банков",
      banksHint: "Публично опубликованные предложения. Мы не рекомендуем банк — только сравниваем, выбор за вами.",
      th: { bank: "Банк", rate: "Ставка", term: "Срок", max: "Макс." },
      years: "лет",
      banksNote:
        "Источник: bank.uz на 12 августа 2026 г. Ставки меняются — уточните условия в банке. Это не реклама и не рекомендация, а сравнение открытых данных.",
      disclaimer:
        "Расчёт предназначен для планирования и не является лицензированной финансовой консультацией. Условия банков и критерии программ взяты из открытых источников (12 августа 2026 г.) и могут измениться.",
    },
    tax: {
      title: "Вы переплачиваете налоги?",
      subtitle:
        "Сравниваем режимы 2026 года. Неверный режим съедает деньги каждый месяц — и в отчёте этот убыток не виден.",
      formTitle: "Расчёт налогов",
      formHint: "Сравним режимы 2026 года и найдём самый дешёвый.",
      f: {
        revenue: "Оборот в месяц (сум)",
        sector: "Отрасль",
        employees: "Количество сотрудников",
        salary: "Средняя зарплата",
        rent: "Аренда и прочие расходы в месяц",
        individual: "Я ИП / самозанятый",
      },
      submit: "Рассчитать",
      empty: "Введите оборот — покажем, какой режим дешевле и сколько стоит неверный режим в год.",
      headlineLabel: "Во сколько обходится неверный режим",
      headlineCaption:
        "Каждый год. Самый дешёвый режим — {regime}. Многие предприниматели этого не знают, потому что убыток не виден — он просто списывается каждый месяц.",
      warnOverOneBillion:
        "Ваш годовой оборот превысил 1 млрд сум — льготная ставка 1% для ИП больше не применяется.",
      warnOverFiveBillion:
        "Ваш годовой оборот превысил 5 млрд сум — переход на общий режим (НДС + налог на прибыль) обязателен.",
      compareTitle: "Сравнение режимов",
      annualRevenue: "Годовой оборот",
      cheapest: "самый дешёвый",
      monthlyIs: "{amount} сум в месяц · {pct}% от оборота",
      notEligible: "Не подходит",
      disclaimer:
        "Расчёт приблизительный: НДС смоделирован как 12% от добавленной стоимости, налог на прибыль — как 15% от операционной прибыли. В реальной отчётности учитывается входной НДС, правила вычета расходов и отраслевые льготы. Подтвердите у бухгалтера или на soliq.uz.",
      engineDisclaimer:
        "Расчёт приблизительный и предназначен для планирования. Ставки взяты из открытых источников на 12 августа 2026 г. Перед принятием решения подтвердите у бухгалтера или на soliq.uz.",
    },
    ai: {
      button: "Совет ИИ",
      loadingButton: "Готовится…",
      title: "Совет ИИ",
      subtitle: "Gemini объясняет ваши цифры — расчёт не меняется",
      loading: "Совет готовится…",
      unavailable: "ИИ-советник сейчас не ответил. Цифры выше — они рассчитаны точно, без ИИ.",
      note: "Цифры рассчитаны детерминированным кодом; ИИ только объясняет. Это не лицензированная финансовая консультация.",
      close: "Закрыть",
    },
    chat: {
      title: "Финансовый советник",
      subtitle:
        "Напишите вопрос или выберите готовый. Советник спросит нужные данные и выполнит расчёт сам.",
      placeholder: "Например: стоит ли открывать кафе в Навои?",
      send: "Отправить",
      restart: "Сначала",
      greeting:
        "Здравствуйте! Я советник Phoenix AI. Помогу с бизнес-планом, кредитом, налогами и льготами. Что вас интересует?",
      suggestions: [
        "Будет ли мой бизнес прибыльным?",
        "Потяну ли я этот кредит?",
        "Какой налоговый режим дешевле?",
        "Какие льготы мне положены?",
      ],
      thinking: "Считаю…",
      engineNote:
        "Ответы советника считаются теми же калькуляторами, что и выше — цифры не выдумываются.",
      openTool: "Открыть на полной странице",
    },
  },

  en: {
    brandTagline: "From idea to growth",
    currency: "so'm",
    perMonth: "so'm/mo",
    perYear: "so'm/yr",
    months: "mo",
    people: "",
    free: "Your workspace · every tool on one profile",
    sourcesAsOf: "Data as of 12 August 2026",
    back: "← Home",
    unverified: "needs confirmation",
    tools: {
      plan: "Business plan",
      credit: "Credit & benefits",
      tax: "Tax",
      chat: "Advisor",
    },
    landing: {
      eyebrow: "AI finance advisor for small entrepreneurs",
      titleA: "Can't afford an accountant?",
      titleB: "Then let this do the maths for you.",
      subtitle:
        "Business plan, credit, tax and location — all in one place. Exact numbers, an answer in 30 seconds, plain language.",
      ctaPrimary: "Run a business plan",
      ctaSecondary: "Check my benefits",
      statLabel: "The gap entrepreneurs never see",
      statCaption:
        "The same {amount} so'm loan over {months} months: at {best}% you save this much versus {market}%. Entrepreneurs never see the gap — because they walk into a single bank.",
      statSource: "Rates: bank.uz, 12 August 2026. This figure was computed live on this page.",
      trustA: "Maths does the calculating, not the AI",
      trustB: "Every number carries a source and a date",
      trustC: "Assumptions are visible and editable",
      painTitle: "The problem isn't convenience — it's money",
      painSub:
        "A small entrepreneur cannot afford an accountant or a consultant. So financial decisions get made blind. And those decisions cost real money.",
      pains: [
        { title: "The wrong tax regime", text: "Pick the wrong regime at registration and you overpay every month. You won't find out at year end either — the loss is invisible, so nobody fixes it." },
        { title: "A loan you can't carry", text: "The bank shows you the monthly payment. It does not answer \"can your business actually carry this?\" — that isn't its job." },
        { title: "The benefit you never heard of", text: "Your age, sector or region may qualify you for a subsidised programme. The bank won't mention it — it is selling its own product." },
      ],
      featTitle: "What it does",
      featSub: "Four tools, one business profile. Enter it once — everything works.",
      feats: [
        { title: "Business plan", text: "Break-even point, customers needed per day, payback period. It ends in a clear verdict, not a spreadsheet." },
        { title: "Credit & benefits", text: "Credit load — what share of revenue the payment eats. Plus the state programmes you qualify for but never heard of." },
        { title: "Tax calculation", text: "We compare the 2026 regimes and pick the cheapest. You see, in numbers, what the wrong one costs per year." },
        { title: "Location analysis", text: "The same business gives different answers in Tashkent and Navoi. Switch the city and watch the verdict change." },
      ],
      trustTitle: "Why you can trust this",
      trustSub: "Because our revenue does not depend on your loan.",
      contrast: [
        { who: "A bank", says: "“We can lend you this. Here's the monthly payment.”" },
        { who: "A lending platform", says: "“We'll forward your application to several banks.”" },
        { who: "Phoenix AI", says: "“Don't take this loan — it eats 31% of your revenue. Lower the rent first.”" },
      ],
      stepsTitle: "How it works",
      steps: [
        { title: "Describe your business once", text: "Sector, city, capital, staff, rent — eight questions. We never ask again." },
        { title: "The numbers compute themselves", text: "Deterministic code does the maths, not a language model. It cannot get the arithmetic wrong." },
        { title: "You get a straight answer", text: "“Works”, “borderline” or “not advisable” — with the reasons attached." },
        { title: "You know what to do next", text: "Which tax regime, which city, which loan — a concrete recommendation for each." },
      ],
      finalTitle: "Will your business make money?",
      finalText: "Signing in takes a minute — the answer takes 30 seconds.",
      finalCta: "Start the calculation",
      disclaimer:
        "Disclaimer: this platform is for information and planning and is not licensed financial or tax advice. Tax rates and bank terms come from public sources (12 August 2026) and can change. Confirm with an accountant or the bank before acting. We do not recommend any specific bank — we compare published information.",
    },
    plan: {
      title: "Will your business make money?",
      subtitle:
        "Enter your numbers — you'll immediately see the break-even point, payback period, cheapest tax regime and a city comparison.",
      formTitle: "About your business",
      formHint: "Eight questions — an answer in 30 seconds.",
      f: {
        name: "Business name",
        sector: "Business type",
        location: "City / location",
        capital: "Starting capital",
        employees: "Number of employees",
        rent: "Monthly rent (so'm)",
        product: "Product / service",
        goal: "Goal",
      },
      submit: "Calculate",
      nameRequired: "Enter a business name.",
      empty: "Enter your numbers — we'll tell you plainly whether this business makes money.",
      m: {
        breakEven: "Break-even revenue",
        daily: "Customers needed daily",
        profit: "Monthly net profit",
        payback: "Payback period",
        util: "Capacity used",
        fixed: "Fixed costs",
      },
      compareTitle: "Location comparison",
      compareDiffer: "{bestCity}: {bestVerdict}. {otherCity}: {otherVerdict}. Same business, different city — different outcome.",
      compareSame: "Both cities give the same result: {bestVerdict}. Fastest payback: {bestCity}.",
      best: "best option",
      cmp: {
        breakEven: "Break-even",
        daily: "Customers/day",
        profit: "Net profit",
        payback: "Payback",
        salary: "Wage (estimate)",
        noPayback: "never pays back",
      },
      taxTitle: "Which tax regime is cheaper?",
      taxBest: "The cheapest regime is {regime}. The wrong one costs you {amount} so'm a year.",
      recTitle: "What to do",
      assumeTitle: "Assumptions used in this calculation",
      assumeNote:
        "These are planning benchmarks, not measured statistics. If your numbers differ, the result changes — nothing is hidden.",
      disclaimer:
        "This calculation is for planning and is not licensed financial or tax advice. Rates come from public sources as of 12 August 2026. Confirm with an accountant.",
    },
    credit: {
      title: "Can you carry this loan?",
      subtitle:
        "Find out before you sign. Monthly payment, credit load, a bank comparison, and the subsidised programmes you qualify for.",
      formTitle: "Credit & benefits",
      formHint: "Enter the bank's offer — we'll check whether something cheaper exists.",
      f: {
        principal: "Loan amount (so'm)",
        months: "Term (months)",
        rate: "Bank rate (%)",
        revenue: "Your monthly revenue (so'm)",
        age: "Your age",
        sector: "Sector",
        priorLoan: "I've had a microloan before (clean credit history)",
        collateral: "I have collateral",
      },
      submit: "Check",
      invalid: "Enter the loan amount and the term.",
      empty: "Enter the bank's offer — we'll tell you whether a programme applies and whether you can carry this loan.",
      headlineLabel: "The benefit you didn't know about",
      headlineCaption:
        "Through the {program} programme at {rate}% you save this much versus {entered}%. Monthly payment {before} → {after} so'm.",
      m: {
        monthly: "Monthly payment",
        total: "Total repaid",
        interest: "Interest paid",
        overpay: "Interest share",
      },
      programsTitle: "Programmes you qualify for",
      programsHint: "Matched on your age, sector, credit history and collateral.",
      noPrograms:
        "No programme matches the details entered. Change the age, sector or credit history and the result changes.",
      forWhom: "Who qualifies",
      saving: "Saving",
      source: "Source",
      link: "link",
      banksTitle: "Bank comparison",
      banksHint: "Publicly published offers. We don't recommend a bank — we compare, you choose.",
      th: { bank: "Bank", rate: "Rate", term: "Term", max: "Max" },
      years: "yr",
      banksNote:
        "Source: bank.uz as of 12 August 2026. Rates change — confirm final terms with the bank. This list is not advertising or a recommendation, it is a comparison of public information.",
      disclaimer:
        "This calculation is for planning and is not licensed financial advice. Bank terms and programme criteria come from public sources (12 August 2026) and can change.",
    },
    tax: {
      title: "Are you overpaying tax?",
      subtitle:
        "We compare the 2026 regimes. The wrong one eats money every month — and that loss never shows up in a report.",
      formTitle: "Tax calculation",
      formHint: "We compare the 2026 regimes and find the cheapest.",
      f: {
        revenue: "Monthly revenue (so'm)",
        sector: "Sector",
        employees: "Number of employees",
        salary: "Average wage",
        rent: "Monthly rent and other costs",
        individual: "I'm a sole trader / self-employed",
      },
      submit: "Calculate",
      empty: "Enter your revenue — we'll show which regime is cheaper and what the wrong one costs per year.",
      headlineLabel: "What the wrong regime costs you",
      headlineCaption:
        "Every year. The cheapest regime is {regime}. Most entrepreneurs never find out, because the loss is invisible — it simply drains away each month.",
      warnOverOneBillion:
        "Your annual turnover passed 1 bln so'm — the 1% reduced rate for sole traders no longer applies.",
      warnOverFiveBillion:
        "Your annual turnover passed 5 bln so'm — moving to the general regime (VAT + profit tax) becomes mandatory.",
      compareTitle: "Regime comparison",
      annualRevenue: "Annual revenue",
      cheapest: "cheapest",
      monthlyIs: "{amount} so'm a month · {pct}% of revenue",
      notEligible: "Not eligible",
      disclaimer:
        "This is an estimate: VAT is modelled as 12% of value added and profit tax as 15% of operating profit. Real filings involve input-VAT offsets, deductible-expense rules and sector exemptions. Confirm with an accountant or soliq.uz.",
      engineDisclaimer:
        "This is a planning estimate. Rates come from public sources as of 12 August 2026. Confirm with an accountant or soliq.uz before acting.",
    },
    ai: {
      button: "AI advice",
      loadingButton: "Preparing…",
      title: "AI advice",
      subtitle: "Gemini explains your figures — the maths never changes",
      loading: "Preparing the advice…",
      unavailable: "The AI advisor didn't respond right now. The figures above were computed exactly, without AI.",
      note: "Figures come from deterministic code; the AI only explains them. This is not licensed financial advice.",
      close: "Close",
    },
    chat: {
      title: "Finance advisor",
      subtitle:
        "Type a question or pick a suggested one. The advisor asks for what it needs and runs the calculation itself.",
      placeholder: "For example: should I open a cafe in Navoi?",
      send: "Send",
      restart: "Start over",
      greeting:
        "Hello! I'm the Phoenix AI advisor. I help with business plans, credit, tax and benefits. What would you like to work out?",
      suggestions: [
        "Will my business make money?",
        "Can I carry this loan?",
        "Which tax regime is cheaper?",
        "What benefits do I qualify for?",
      ],
      thinking: "Calculating…",
      engineNote:
        "The advisor's answers are produced by exactly the same calculators as the pages above — no number is guessed.",
      openTool: "Open the full page",
    },
  },
} as const;

export function copy(lang: FinanceLang): FinanceCopy {
  return COPY[lang] as FinanceCopy;
}

/** Locale-aware thousands formatting for so'm amounts. */
export function formatMoney(value: number, lang: FinanceLang): string {
  const locale = lang === "ru" ? "ru-RU" : lang === "en" ? "en-US" : "ru-RU";
  return value.toLocaleString(locale).replace(/,/g, " ");
}
