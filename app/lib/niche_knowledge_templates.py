"""
Pre-built FAQ / knowledge-base entries seeded into every new bot by niche.

Each niche maps to a sequence of ``(question, answer)`` pairs written in English.
The bot's AI layer translates responses to the end-user's language at runtime, so
all templates are kept in English for maximum retrieval quality.

Template content is intentionally **generic** — it covers the most common questions
a first-time bot owner would want answered out-of-the-box.  Owners can delete the
seeded knowledge file or add their own docs afterward.
"""

from __future__ import annotations

from typing import NamedTuple


class KBTemplate(NamedTuple):
    """Single FAQ entry to seed into a bot's knowledge base."""

    question: str
    answer: str


_EDUCATION_TEMPLATES: tuple[KBTemplate, ...] = (
    KBTemplate(
        question="What programs or courses do you offer?",
        answer=(
            "We offer a range of programs designed for different learning goals and schedules. "
            "Our catalog includes full-time degree programs, part-time certificates, and short "
            "professional courses. Each program page on our website lists prerequisites, duration, "
            "and tuition details. If you tell me which subject area interests you, I can point you "
            "to the right program."
        ),
    ),
    KBTemplate(
        question="How do I apply or enroll?",
        answer=(
            "Applications are accepted online through our enrollment portal. You'll need to create "
            "an account, fill in your personal details, upload any required documents (transcripts, "
            "ID, etc.), and submit the form. After submission, our admissions team reviews your "
            "application and typically responds within 5-7 business days."
        ),
    ),
    KBTemplate(
        question="What are the tuition fees and payment options?",
        answer=(
            "Tuition varies by program. You can find exact fees on each program's page. We accept "
            "full upfront payment, installment plans, and some programs qualify for scholarships or "
            "financial aid. Contact our finance office for a personalized payment plan."
        ),
    ),
    KBTemplate(
        question="Are there scholarships or financial aid available?",
        answer=(
            "Yes, we offer merit-based scholarships, need-based financial aid, and early-bird "
            "discounts for certain programs. Eligibility criteria and application deadlines differ "
            "by scholarship type. Visit our scholarships page or ask me for specific requirements."
        ),
    ),
    KBTemplate(
        question="What is the class schedule and format?",
        answer=(
            "Classes are offered in multiple formats: in-person, online live sessions, and "
            "self-paced modules. Schedules depend on the program — some run weekday mornings, "
            "others evenings or weekends. Check the specific program listing for its calendar, "
            "or let me know your preferred format and I'll suggest matching options."
        ),
    ),
    KBTemplate(
        question="Do you provide certificates upon completion?",
        answer=(
            "Yes, all students who successfully complete their program receive an official "
            "certificate or diploma. Digital certificates are issued within two weeks of "
            "completion and can be verified online. Some programs also prepare you for "
            "industry-recognized certification exams."
        ),
    ),
)

_HEALTHCARE_TEMPLATES: tuple[KBTemplate, ...] = (
    KBTemplate(
        question="How do I book an appointment?",
        answer=(
            "You can book an appointment through our online booking system, by calling our "
            "front desk, or right here in this chat. Please have your preferred date, time, "
            "and the type of service you need ready. We'll confirm your appointment via SMS "
            "or email."
        ),
    ),
    KBTemplate(
        question="What services does the clinic offer?",
        answer=(
            "Our clinic provides general consultations, preventive check-ups, diagnostics, "
            "specialist referrals, and follow-up care. We also offer telemedicine consultations "
            "for non-emergency cases. For a full list of services, please visit our services page "
            "or ask me about a specific health concern."
        ),
    ),
    KBTemplate(
        question="What are your working hours?",
        answer=(
            "Our standard working hours are Monday through Friday, 8:00 AM to 6:00 PM, and "
            "Saturday from 9:00 AM to 2:00 PM. We are closed on Sundays and public holidays. "
            "Emergency services may have different hours — please call our hotline for urgent needs."
        ),
    ),
    KBTemplate(
        question="Do you accept insurance?",
        answer=(
            "Yes, we accept most major insurance plans. Please bring your insurance card to "
            "your appointment. If you're unsure whether your plan is accepted, let me know "
            "your insurance provider and I'll check for you. Self-pay options and payment "
            "plans are also available."
        ),
    ),
    KBTemplate(
        question="How do I prepare for my visit?",
        answer=(
            "Please arrive 10-15 minutes early to complete any registration forms. Bring a "
            "valid ID, your insurance card, a list of current medications, and any recent test "
            "results or medical records relevant to your visit. If you're coming for a specific "
            "test, your doctor may have given you preparation instructions (e.g., fasting)."
        ),
    ),
    KBTemplate(
        question="Can I get my test results online?",
        answer=(
            "Yes, test results are available through our patient portal once your doctor has "
            "reviewed them. You'll receive a notification when results are ready. For urgent "
            "results, our team will contact you directly. If you need help accessing the portal, "
            "our staff can assist you."
        ),
    ),
)

_DEV_AGENCY_TEMPLATES: tuple[KBTemplate, ...] = (
    KBTemplate(
        question="What types of projects do you handle?",
        answer=(
            "We specialize in web applications, mobile apps (iOS and Android), API integrations, "
            "e-commerce platforms, and custom software solutions. Whether you need an MVP for a "
            "startup or a full enterprise system, we can scope and deliver it. Tell me about your "
            "idea and I'll outline how we can help."
        ),
    ),
    KBTemplate(
        question="How does your development process work?",
        answer=(
            "We follow an agile development process: discovery and scoping, design, iterative "
            "development sprints, QA testing, and deployment. You get regular updates, access to "
            "a staging environment, and sprint demos so you always know what's being built. After "
            "launch, we offer maintenance and support packages."
        ),
    ),
    KBTemplate(
        question="How much does a project typically cost?",
        answer=(
            "Costs depend on project complexity, features, and timeline. A simple MVP might start "
            "from a few thousand dollars, while complex enterprise projects can be significantly "
            "more. We provide a detailed estimate after an initial discovery call where we "
            "understand your requirements. There are no hidden fees."
        ),
    ),
    KBTemplate(
        question="How long does development take?",
        answer=(
            "Timelines vary by project scope. A small MVP can be delivered in 4-8 weeks, "
            "mid-size projects in 2-4 months, and large-scale systems in 6+ months. We'll "
            "give you a realistic timeline during the scoping phase and keep you updated "
            "throughout development."
        ),
    ),
    KBTemplate(
        question="What technologies do you use?",
        answer=(
            "Our tech stack is flexible and chosen based on project needs. We commonly work with "
            "React, Next.js, Vue.js for frontend; Python (FastAPI, Django), Node.js, Go for "
            "backend; PostgreSQL, MongoDB for databases; and AWS, GCP, or Azure for cloud "
            "infrastructure. We'll recommend the best stack for your specific use case."
        ),
    ),
    KBTemplate(
        question="Do you provide post-launch support?",
        answer=(
            "Yes, we offer ongoing maintenance and support plans that include bug fixes, security "
            "updates, performance monitoring, and feature enhancements. Support plans are flexible — "
            "from basic monthly retainers to dedicated team arrangements. We also provide full "
            "documentation and knowledge transfer if you prefer to maintain in-house."
        ),
    ),
)

_SERVICES_TEMPLATES: tuple[KBTemplate, ...] = (
    KBTemplate(
        question="What services do you offer?",
        answer=(
            "We provide a wide range of professional services tailored to your needs. Our "
            "service catalog is available on our website, and I can help you find the right "
            "service based on what you're looking for. Just describe your need and I'll match "
            "you with the best option."
        ),
    ),
    KBTemplate(
        question="How do I request a quote?",
        answer=(
            "You can request a quote right here in this chat, through our website, or by "
            "calling us. I'll need to know the type of service, your location, preferred "
            "dates, and any specific requirements. We typically send quotes within 24 hours."
        ),
    ),
    KBTemplate(
        question="What are your prices?",
        answer=(
            "Pricing depends on the type of service, scope of work, and your location. We "
            "offer competitive rates and transparent pricing with no hidden fees. For a "
            "personalized quote, tell me what you need and I'll provide an estimate."
        ),
    ),
    KBTemplate(
        question="How do I book a service?",
        answer=(
            "Booking is easy — you can schedule online through our website, call us, or book "
            "directly here in this chat. Choose your preferred date and time, and we'll confirm "
            "your booking via email or SMS. We recommend booking at least 48 hours in advance."
        ),
    ),
    KBTemplate(
        question="What areas do you serve?",
        answer=(
            "We serve a wide area and are constantly expanding. Please provide your location "
            "or zip code and I'll confirm whether we cover your area. For locations outside "
            "our standard service zone, we may be able to arrange coverage with additional "
            "travel fees."
        ),
    ),
    KBTemplate(
        question="What is your cancellation policy?",
        answer=(
            "You can cancel or reschedule your booking up to 24 hours before the scheduled "
            "time at no charge. Cancellations within 24 hours may incur a fee. We understand "
            "that plans change — just let us know as early as possible and we'll do our best "
            "to accommodate."
        ),
    ),
)

# ── Public registry ────────────────────────────────────────────────────────────

NICHE_KNOWLEDGE_TEMPLATES: dict[str, tuple[KBTemplate, ...]] = {
    "education": _EDUCATION_TEMPLATES,
    "healthcare": _HEALTHCARE_TEMPLATES,
    "dev_agency": _DEV_AGENCY_TEMPLATES,
    "services": _SERVICES_TEMPLATES,
}


def get_knowledge_templates(niche_id: str) -> tuple[KBTemplate, ...]:
    """Return FAQ templates for *niche_id*, or an empty tuple when none are configured."""
    return NICHE_KNOWLEDGE_TEMPLATES.get(niche_id, ())
