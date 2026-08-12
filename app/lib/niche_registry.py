"""
Config-driven niche registry for bot onboarding and validation.

Funnel shape and per-turn questions live in :mod:`app.lib.niche_flow` (one
:class:`~app.lib.niche_flow.schema.NicheConversationFlowDefinition` per niche id).
Keep ``NicheDefinition.id`` values aligned with :func:`~app.lib.niche_flow.registry.supported_niche_flow_ids`
(Sprint 8 lead/CRM code should treat both as the same key namespace).

**Single source of truth:** niche ids, labels, descriptions, wizard copy, and supported goals are
defined here. The HTTP catalog at ``GET /api/v1/catalog/niches`` exposes this to clients.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

# Must stay aligned with ``ALLOWED_GOAL_TYPES`` in :mod:`app.schemas.bots`.
STANDARD_BOT_GOAL_TYPES: tuple[str, ...] = ("support", "sales", "faq", "consulting")


@dataclass(frozen=True, slots=True)
class NicheDefinition:
    id: str
    label: str
    short_description: str
    wizard_hint: str
    icon_key: str
    supported_goals: tuple[str, ...]
    onboarding_hints: tuple[str, ...]
    default_lead_fields: tuple[str, ...]
    qualification_questions: tuple[str, ...] = ()
    scoring_rules: tuple[str, ...] = ()
    crm_mapping: MappingProxyType[str, str] = MappingProxyType({})
    prompt_templates: MappingProxyType[str, str] = MappingProxyType({})
    default_welcome_messages: MappingProxyType[str, str] = MappingProxyType({})
    visible: bool = True


_NICHE_LIST: tuple[NicheDefinition, ...] = (
    NicheDefinition(
        id="education",
        label="Education",
        short_description="Capture learner intent, program fit, and enrollment readiness.",
        wizard_hint="Admissions, courses, student support",
        icon_key="graduation-cap",
        supported_goals=STANDARD_BOT_GOAL_TYPES,
        onboarding_hints=("Start with program interest and timeline questions.",),
        default_lead_fields=("full_name", "email", "phone", "program_interest"),
        default_welcome_messages=MappingProxyType({
            "en": "Hi there! Welcome! I'm here to help you explore our programs and find the right fit for your learning journey. What would you like to know?",
            "uz": "Salom! Xush kelibsiz! Men sizga o'quv dasturlarimizni tanlashda yordam beraman. Sizni nima qiziqtiradi?",
            "ru": "Здравствуйте! Добро пожаловать! Я помогу вам подобрать подходящую программу обучения. Что бы вы хотели узнать?",
            "es": "Hola! Bienvenido/a! Estoy aqui para ayudarte a explorar nuestros programas. Que te gustaria saber?",
            "de": "Hallo! Willkommen! Ich helfe Ihnen gerne, das passende Programm zu finden. Was moechten Sie wissen?",
            "fr": "Bonjour! Bienvenue! Je suis la pour vous aider a trouver le programme ideal. Que souhaitez-vous savoir?",
        }),
    ),
    NicheDefinition(
        id="healthcare",
        label="Healthcare / Clinic",
        short_description="Qualify appointment requests and route patient inquiries responsibly.",
        wizard_hint="Appointments, triage, and patient FAQs",
        icon_key="stethoscope",
        supported_goals=STANDARD_BOT_GOAL_TYPES,
        onboarding_hints=("Keep triage language careful; escalate when unsure.",),
        default_lead_fields=("full_name", "phone", "email", "service_interest"),
        default_welcome_messages=MappingProxyType({
            "en": "Hello! Welcome to our clinic. I can help you with appointment scheduling, service information, and general inquiries. How can I assist you today?",
            "uz": "Salom! Klinikamizga xush kelibsiz. Qabulga yozilish, xizmatlar va umumiy savollar bo'yicha yordam bera olaman. Bugun sizga qanday yordam beray?",
            "ru": "Здравствуйте! Добро пожаловать в нашу клинику. Я помогу вам с записью на приём, информацией об услугах и общими вопросами. Чем могу помочь?",
            "es": "Hola! Bienvenido/a a nuestra clinica. Puedo ayudarte con citas, informacion de servicios y consultas generales. Como puedo ayudarte hoy?",
            "de": "Hallo! Willkommen in unserer Klinik. Ich helfe Ihnen gerne bei Terminvereinbarungen, Informationen und allgemeinen Fragen. Wie kann ich Ihnen helfen?",
            "fr": "Bonjour! Bienvenue dans notre clinique. Je peux vous aider pour les rendez-vous, les informations sur nos services et vos questions. Comment puis-je vous aider?",
        }),
    ),
    NicheDefinition(
        id="dev_agency",
        label="Dev / Agency",
        short_description="Collect project scope, budget signal, and timeline expectations.",
        wizard_hint="Project intake, scope, and client comms",
        icon_key="code",
        supported_goals=STANDARD_BOT_GOAL_TYPES,
        onboarding_hints=("Capture scope and budget signal before hand-off.",),
        default_lead_fields=("full_name", "work_email", "company", "project_scope"),
        default_welcome_messages=MappingProxyType({
            "en": "Hey! Thanks for reaching out. I'm here to help you get started with your project. Tell me about what you're building and I'll connect you with the right team.",
            "uz": "Salom! Murojaat qilganingiz uchun rahmat. Loyihangiz haqida gapirib bering, sizni kerakli jamoaga yo'naltirib beraman.",
            "ru": "Привет! Спасибо за обращение. Расскажите о вашем проекте, и я свяжу вас с нужной командой.",
            "es": "Hola! Gracias por contactarnos. Cuentame sobre tu proyecto y te conectare con el equipo adecuado.",
            "de": "Hallo! Danke fuer Ihre Anfrage. Erzaehlen Sie mir von Ihrem Projekt und ich verbinde Sie mit dem richtigen Team.",
            "fr": "Bonjour! Merci de nous avoir contactes. Parlez-moi de votre projet et je vous mettrai en relation avec la bonne equipe.",
        }),
    ),
    NicheDefinition(
        id="services",
        label="Services",
        short_description="Capture job type, location, and preferred follow-up for local services.",
        wizard_hint="Bookings, quotes, and service requests",
        icon_key="briefcase",
        supported_goals=STANDARD_BOT_GOAL_TYPES,
        onboarding_hints=("Ask for service type and service area early.",),
        default_lead_fields=("full_name", "phone", "service_type", "location"),
        default_welcome_messages=MappingProxyType({
            "en": "Hello! Welcome! I'm here to help you find the right service and get a quick quote. What type of service are you looking for?",
            "uz": "Salom! Xush kelibsiz! Sizga kerakli xizmatni topish va narx olishda yordam beraman. Qanday xizmat qidiryapsiz?",
            "ru": "Здравствуйте! Добро пожаловать! Я помогу вам подобрать нужную услугу и рассчитать стоимость. Какой тип услуги вас интересует?",
            "es": "Hola! Bienvenido/a! Estoy aqui para ayudarte a encontrar el servicio adecuado. Que tipo de servicio buscas?",
            "de": "Hallo! Willkommen! Ich helfe Ihnen gerne, den passenden Service zu finden. Welche Art von Service suchen Sie?",
            "fr": "Bonjour! Bienvenue! Je suis la pour vous aider a trouver le bon service. Quel type de service recherchez-vous?",
        }),
    ),
)

_NICHE_BY_ID: MappingProxyType[str, NicheDefinition] = MappingProxyType(
    {niche.id: niche for niche in _NICHE_LIST}
)


def list_supported_niches() -> tuple[NicheDefinition, ...]:
    """Return all configured niches in display order."""
    return _NICHE_LIST


def get_niche_by_id(niche_id: str) -> NicheDefinition | None:
    """Return a niche definition or None when the id is not configured."""
    return _NICHE_BY_ID.get((niche_id or "").strip())


def validate_niche_id(niche_id: str) -> bool:
    """Fast validation helper for DTO/service guards."""
    return get_niche_by_id(niche_id) is not None


def list_visible_niche_definitions() -> tuple[NicheDefinition, ...]:
    """Niches exposed in product UI (catalog, wizard)."""
    return tuple(n for n in _NICHE_LIST if n.visible)


def get_default_welcome_message(niche_id: str, language: str | None = None) -> str | None:
    """Return the niche's default welcome message for *language*, falling back to ``"en"``.

    Returns ``None`` when the niche has no welcome messages configured.
    The *language* value is normalised: ``"en-US"`` → ``"en"``, ``None`` → ``"en"``.
    """
    niche = get_niche_by_id(niche_id)
    if niche is None or not niche.default_welcome_messages:
        return None
    lang = (language or "en").strip().lower()[:2]
    return niche.default_welcome_messages.get(lang) or niche.default_welcome_messages.get("en")
